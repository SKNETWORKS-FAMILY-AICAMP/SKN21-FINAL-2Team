import asyncio
import re
import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.output import IntentCoreOutput, SummaryOutput, IntentType, IntentSlots, InputType
from app.agents.prompts.prompts import INTENT_PROMPT, SUMMARY_PROMPT, IMAGE_INTENT_TYPE, get_summary_language_instruction
from app.agents.models.state import TravelState
from app.core.llm_factory import LLMFactory
from app.agents.models.output import CategoryType
from app.utils.geocoder import NormalizedLocation
from app.utils.common import in_seoul_bbox, dprint
from app.utils.vision import describe_image


_TAG_EXPANSION: dict[str, list[str]] = {
    "한국적인":  ["한옥", "전통", "전통차", "고즈넉한"],
    "전통적인":  ["한옥", "전통", "전통차", "고즈넉한"],
    "한옥":      ["한옥", "전통", "고즈넉한"],
    "힙한":      ["감성카페", "인더스트리얼", "트렌디한"],
    "감성적인":  ["감성카페", "빈티지소품", "인스타감성"],
    "인스타감성": ["감성카페", "포토존", "인스타"],
    "레트로":    ["빈티지", "복고", "근대건축"],
    "복고풍":    ["빈티지", "복고", "근대건축"],
    "아늑한":    ["조용한", "소규모", "따뜻한"],
    "포근한":    ["조용한", "소규모", "따뜻한"],
}


def _expand_input_tags(tags: list[str]) -> list[str]:
    expanded = list(tags)
    for tag in tags:
        for key, additions in _TAG_EXPANSION.items():
            if key in tag:
                expanded.extend(additions)
    return list(dict.fromkeys(expanded))  # 순서 유지 + 중복 제거


_CRIME_PATTERN = re.compile(
    r"살해|살인|살육|살상|"
    r"시신|시체|"
    r"성폭행|강간|추행|몰카|불법촬영|"
    r"테러|폭탄|폭발물|"
    r"간첩|기밀유출|국가보안법"
)


async def _analyze_image(image_path: str) -> str | None:
    """이미지 분석 + custom event 발행 (pipeline 'image_analysis' step 표시용)"""
    try:
        await adispatch_custom_event("image_analysis", {"status": "start"})
    except RuntimeError:
        pass
    try:
        result = await describe_image(image_path)
    except Exception as e:
        dprint(f"[Intent] describe_image failed: {e}")
        result = None
    try:
        await adispatch_custom_event("image_analysis", {"status": "done"})
    except RuntimeError:
        pass
    return result


async def intent_node(state: TravelState):
    """
    사용자 의도 분석 Agent
    - DB 접근 없이, state에 주입된 prefs_info를 그대로 사용
    - 대화 요약(summary_message)도 여기서 누적 업데이트
    - 요약과 의도 분석을 병렬로 실행하여 지연 최소화
    """
    _intent_start = time.perf_counter()
    dprint("--- Intent Agent ---")
    try:
        await adispatch_custom_event("pipeline_step", {"node": "intent", "status": "start"})
    except RuntimeError:
        pass

    # API 레이어에서 주입된 사용자 선호도 정보 사용
    dprint(f"[Intent] state keys: {list(state.keys())}")
    prefs_info = state.get("prefs_info", "[DEBUG] PREFS_INFO_MISSING_IN_STATE")

    user_input = state.get("user_input")
    image_path = state.get("input_image")
    summary_title = state.get("summary_title", "제목 없음")
    summary_message = state.get("summary_message", "아직 대화 요약 없음")

    # 이미지가 있으면 가장 먼저 분석 (결과를 state에 저장하여 이후 노드에서 재사용)
    semantic_input_image = state.get("semantic_input_image")
    if image_path and not semantic_input_image:
        dprint("[Intent] Analyzing image before LLM intent...")
        _t0 = time.perf_counter()
        semantic_input_image = await _analyze_image(image_path)
        dprint(f"[TIMING] intent describe_image elapsed={time.perf_counter()-_t0:.3f}s  result={repr(semantic_input_image)[:80]}")

    if not user_input and not image_path:
        return {
            "intents": [IntentType.GENERAL],
            "primary_intent": IntentType.GENERAL,
        }

    # 최근 6개 메시지만 사용
    messages = state.get("messages", [])[-6:]

    # LLM 및 Structured Output 설정
    llm = LLMFactory.get_llm()
    intent_llm = llm.with_structured_output(IntentCoreOutput)
    summary_llm = llm.with_structured_output(SummaryOutput)

    human_input = user_input
    if semantic_input_image:
        human_input += f"\n입력 이미지에 대한 설명 : {semantic_input_image}"

    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", INTENT_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", human_input)
    ])
    summary_prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARY_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", human_input)
    ])

    intent_chain = intent_prompt | intent_llm
    summary_chain = summary_prompt | summary_llm

    dprint(f"[Intent] Prefs info from state: {prefs_info}")

    _llm_start = time.perf_counter()
    dprint(f"[TIMING] intent+summary LLM parallel START  messages={len(messages)}  has_image={'yes' if image_path else 'no'}")
    result, summary_result = await asyncio.gather(
        intent_chain.ainvoke({
            "messages": messages,
            "category_desc": CategoryType.description(),
            "summary_title": summary_title,
            "summary_message": summary_message,
            "image_intent_type": IMAGE_INTENT_TYPE if image_path else "",
        }),
        summary_chain.ainvoke({
            "messages": messages,
            "summary_title": summary_title,
            "summary_message": summary_message,
            "summary_language_instruction": get_summary_language_instruction(state.get("language")),
        }),
    )
    dprint(f"[TIMING] intent+summary LLM parallel DONE  elapsed={time.perf_counter()-_llm_start:.3f}s")

    dprint("Intent Result : ", result)
    dprint("Summary Result : ", summary_result)

    primary_intent = result.primary_intent
    update_user_input = result.update_user_input or ""

    # --- 범죄 관련 입력 강제 차단 (Python-level 이중 방어) ---
    check_input = (update_user_input or user_input or "")
    if _CRIME_PATTERN.search(check_input):
        dprint(f"[Intent] Crime pattern detected — forcing GENERAL intent")
        primary_intent = IntentType.GENERAL
        result.intents = [IntentType.GENERAL]
        if result.slots:
            result.slots.location = None
            result.slots.categories = None

    # --- 표준 장소 후처리: LLM 반환 location을 서버에서 최종 정규화 ---
    # 조건 기준: canonical_matched 여부 (이름 변경 여부 X)
    # → LLM이 canonical key와 동일한 이름을 반환해도 lat/lon이 환각일 수 있으므로
    #   사전 매칭이 성공한 경우 항상 사전 좌표로 덮어쓴다.
    slots = result.slots
    if slots and slots.location:
        if slots.location.name:
            norm = NormalizedLocation.normalize_location(slots.location.name)
            if norm.canonical_matched and norm.lat is not None:
                # 사전 매칭 성공 → 이름·좌표 모두 사전 값으로 확정
                if norm.normalized_location and norm.normalized_location != slots.location.name:
                    slots.location.name = norm.normalized_location
                slots.location.lat = norm.lat
                slots.location.lon = norm.lon
                dprint(
                    f"[Intent] location resolved from LANDMARK_DICTIONARY: {slots.location.name!r} "
                    f"lat={norm.lat} lon={norm.lon} (canonical_matched=True)"
                )

        if slots.location.lat and slots.location.lon:
            if not in_seoul_bbox(slots.location.lat, slots.location.lon):
                # 좌표가 서울 밖에 있으면 일반 검색으로 변경
                primary_intent = IntentType.GENERAL

    expanded_tags = _expand_input_tags(result.input_tags or [])
    dprint(f"[Intent] input_tags expanded: {result.input_tags} → {expanded_tags}")

    new_summary_title = summary_result.summary_title
    if new_summary_title and new_summary_title.strip().lower() == "null":
        new_summary_title = None

    # State에 결과 저장
    dprint(f"[TIMING] intent_node DONE  total={time.perf_counter()-_intent_start:.3f}s  primary_intent={primary_intent}")
    return {
        "intents": result.intents,
        "primary_intent": primary_intent,
        "slots": slots,
        "update_user_input": update_user_input,
        "summary_title": new_summary_title or summary_title,
        "summary_message": summary_result.summary_message,
        "input_tags": expanded_tags,
        "prefs_info": prefs_info,
        "semantic_input_image": semantic_input_image,
        "candidates": [],
        "candidate_pool": [],
        "place_info_list": [],
    }
