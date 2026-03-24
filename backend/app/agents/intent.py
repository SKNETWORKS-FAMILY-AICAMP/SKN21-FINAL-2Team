import asyncio
import re
import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.manager import adispatch_custom_event

from app.agents.models.output import IntentCoreOutput, SummaryOutput, IntentType
from app.agents.prompts.prompts import INTENT_PROMPT, SUMMARY_PROMPT, IMAGE_INTENT_TYPE, get_language_instruction
from app.agents.models.state import TravelState
from app.core.llm_factory import LLMFactory
from app.agents.models.output import CategoryType
from app.utils.geocoder import NormalizedLocation, GeoCoder
from app.utils.common import in_seoul_bbox, dprint
from app.utils.vision import describe_image
from app.utils.weather import fetch_weather, fetch_weather_for_date


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

    # 이전 턴에 이미 dates가 있으면 날짜별 날씨를 초기 gather에 포함 (순차 대기 제거)
    _prev_slots = state.get("slots")
    _prev_dates_str = getattr(_prev_slots, "dates", None) if _prev_slots else None
    _lat = state.get("input_lat")
    _lon = state.get("input_lon")
    _gps_in_seoul = bool(_lat and _lon and in_seoul_bbox(_lat, _lon))
    _gps_outside_seoul = bool(_lat and _lon and not _gps_in_seoul)

    _llm_start = time.perf_counter()
    dprint(
        f"[TIMING] intent START  messages={len(messages)}  "
        f"has_image={'yes' if image_path else 'no'}  prev_dates={_prev_dates_str!r}  "
        f"gps_in_seoul={_gps_in_seoul}  gps_outside_seoul={_gps_outside_seoul}"
    )

    # ── 1차 gather: weather + GPS geocoding (빠른 API 호출만, ~200ms) ─────────
    # GPS geocoding은 intent LLM에 위치 컨텍스트를 주입하기 위해 먼저 완료해야 한다.
    # summary LLM(~2s)은 intent LLM과 함께 2차 gather에서 병렬 실행한다.
    fast_coro_keys: list[str] = ["weather"]
    fast_coros: list = [fetch_weather(_lat, _lon)]
    if _lat and _lon:
        fast_coro_keys.append("gps")
        fast_coros.append(GeoCoder.get_address(_lat, _lon))
    if _prev_dates_str:
        fast_coro_keys.append("date_weather")
        fast_coros.append(fetch_weather_for_date(_lat, _lon, _prev_dates_str))

    fast_results = dict(zip(fast_coro_keys, await asyncio.gather(*fast_coros)))
    weather_info = fast_results["weather"]
    prefetched_date_weather = fast_results.get("date_weather")

    # GPS 주소 처리 및 gps_location_context 빌드
    input_address: str | None = state.get("input_address")  # 이전 턴 값 기본값
    gps_outside_seoul: bool = state.get("gps_outside_seoul", False)
    if "gps" in fast_results:
        _gps_addr = fast_results["gps"] or None   # GeoCoder.get_address는 str 반환, 빈 문자열 → None
        if _gps_addr:
            input_address = _gps_addr
        gps_outside_seoul = _gps_outside_seoul

    if input_address:
        _suffix = "(서울 내)" if _gps_in_seoul else "(서울 외 지역)"
        _instruction = (
            "- 사용자 입력에 명시적 장소가 없으면 이 지역을 location.name으로 우선 사용하십시오."
            if _gps_in_seoul else
            "- 사용자의 현재 위치가 서울 밖입니다. location은 None으로 두고, 서울 장소 추천 intent는 유지하십시오."
        )
        gps_location_context = (
            f"## 사용자 첨부 위치 (GPS)\n"
            f"- 현재 위치: {input_address} {_suffix}\n"
            f"{_instruction}"
        )
    else:
        gps_location_context = ""

    dprint(f"[TIMING] fast-gather DONE  elapsed={time.perf_counter()-_llm_start:.3f}s  gps_ctx={bool(gps_location_context)}")

    # ── 2차 gather: intent LLM + summary LLM 병렬 실행 (~2s) ──────────────────
    result, summary_result = await asyncio.gather(
        intent_chain.ainvoke({
            "messages": messages,
            "category_desc": CategoryType.description(),
            "summary_message": summary_message,
            "image_intent_type": IMAGE_INTENT_TYPE if image_path else "",
            "gps_location_context": gps_location_context,
        }),
        summary_chain.ainvoke({
            "messages": messages,
            "summary_title": summary_title,
            "summary_message": summary_message,
            "summary_language_instruction": get_language_instruction(state.get("language"), False),
        }),
    )

    dprint(f"[TIMING] intent+summary LLM DONE  total_elapsed={time.perf_counter()-_llm_start:.3f}s")
    dprint(f"[Intent] weather_info (initial): {weather_info!r}")

    # slots.dates가 있으면 해당 날짜의 날씨로 덮어쓰기 (2단계 — 예보 or 월별 평균)
    # 현재 턴 slots 우선, 없으면 이전 턴 state slots 참조
    _dates_str = (result.slots.dates if result.slots else None) or _prev_dates_str
    if _dates_str:
        if _dates_str == _prev_dates_str and prefetched_date_weather:
            # 이미 병렬로 조회한 결과 재사용 — 추가 API 호출 없음
            weather_info = prefetched_date_weather
            dprint(f"[Intent] weather_info (prefetched) for date={_dates_str!r}: {weather_info!r}")
        else:
            # 이번 턴에 새로운 날짜가 입력된 경우만 추가 조회
            _date_weather = await fetch_weather_for_date(_lat, _lon, _dates_str)
            if _date_weather:
                weather_info = _date_weather
                dprint(f"[Intent] weather_info updated for date={_dates_str!r}: {weather_info!r}")

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
        update_user_input += "\n범죄 관련 내용이 포함되어있으니 장소 추천을 하지 말아줘"
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
        "weather_info": weather_info,
        "input_address": input_address,
        "gps_outside_seoul": gps_outside_seoul,
        "candidates": [],
        "candidate_pool": [],
        "place_info_list": [],
    }
