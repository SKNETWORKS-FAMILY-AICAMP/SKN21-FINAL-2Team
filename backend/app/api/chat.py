import re
import json
import asyncio
import math
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, aliased
from typing import List
from pydantic import BaseModel
from app.database.connection import db_manager, get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from app.models.enums import RoleType
from app.schemas.chat import (
    ChatRoomCreate,
    ChatRoomResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatPlaceResponse,
    BookmarkedRoomResponse,
    BookmarkedPlaceResponse,
    AutoStartChatRoomRequest,
)
from app.utils.security import get_current_user
from app.utils.error_handler import AppException, ErrorCode
from app.utils.common import to_client_image_url
from app.agents.graph import workflow
from app.agents.models.state import TravelState
from app.database.checkpointer import get_checkpointer
from app.models.chat import ChatPlace
from app.services.auto_start_prompt import (
    render_auto_start_prompt,
    render_auto_start_place_prompt,
    render_auto_start_combined_prompt,
    render_auto_start_greeting_prompt,
)

from langchain_core.messages import HumanMessage

_graph_app = None
_checkpointer = None
_graph_app_lock = asyncio.Lock()

async def get_graph_app():
    global _graph_app, _checkpointer
    if _graph_app is not None:
        return _graph_app

    # 다중 요청 시 checkpointer/setup 중복 실행 방지
    async with _graph_app_lock:
        if _graph_app is None:
            print('init graph app')
            _checkpointer = await get_checkpointer()
            _graph_app = workflow().compile(checkpointer=_checkpointer)
            print('compile graph app (with AsyncMySaver checkpointer)')
    return _graph_app

router = APIRouter(prefix="/api/chat", tags=["chat"])

class TodayRecommendationItem(BaseModel):
    id: str
    title: str
    description: str
    prompt: str


def _clean_history_text(value: str) -> str:
    clean = re.sub(r"\s+", " ", (value or "")).strip()
    return clean


def _shorten_text(value: str, limit: int = 64) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."

AUTO_ROOM_TITLES = {"", "새로운 여행 계획", "새 채팅"}

def _make_room_title(text: str) -> str:
    """Generate a concise room title from user input."""
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if len(clean) > 30:
        clean = clean[:30].rstrip() + "..."
    return clean or "새 채팅"


def _should_update_room_title(db: Session, room_id: int) -> bool:
    count = db.query(func.count(ChatMessage.id)).filter(ChatMessage.room_id == room_id).scalar() or 0
    return int(count) <= 2


def _can_overwrite_room_title(room: ChatRoom) -> bool:
    return (room.title or "").strip() in AUTO_ROOM_TITLES


def _save_room_title(db: Session, room: ChatRoom, next_title: str | None) -> bool:
    raw_title = (next_title or "").strip()
    if not raw_title:
        return False

    # 기존 정책(원문 우선)을 유지하되, DB 길이(255) 초과 시에만 축약 제목 사용
    title_to_save = raw_title if len(raw_title) <= 255 else _make_room_title(raw_title)
    if len(title_to_save) > 255:
        title_to_save = title_to_save[:255]

    room.title = title_to_save
    db.add(room)
    try:
        db.commit()
        db.refresh(room)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"[ChatAPI] Room title update failed(room_id={room.id}): {e}")
        return False


def _safe_float(value):
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _normalize_int_or_zero(value) -> int:
    try:
        v = int(value)
        return v if v > 0 else 0
    except (TypeError, ValueError):
        return 0


def _normalize_float_or_zero(value) -> float:
    parsed = _safe_float(value)
    if parsed is None or parsed == 0:
        return 0.0
    return parsed


def _input_coordinate_or_none(value):
    parsed = _safe_float(value)
    if parsed is None or parsed == 0:
        return None
    return parsed


def _get_owned_room_or_404(db: Session, room_id: int, user_id: int) -> ChatRoom:
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == user_id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND, "Room not found", 404)
    return room


def _save_human_message_if_needed(db: Session, room_id: int, message_in: ChatMessageCreate):
    if not message_in.save_user_message:
        return
    user_message = ChatMessage(
        room_id=room_id,
        message=message_in.message,
        role=RoleType.human,
        latitude=_input_coordinate_or_none(message_in.latitude),
        longitude=_input_coordinate_or_none(message_in.longitude),
        image_path=message_in.image_path,
    )
    db.add(user_message)
    db.commit()


def _build_graph_inputs(user: User, room: ChatRoom, message_in: ChatMessageCreate) -> TravelState:
    print(f"[BuildInputs] User({user.id}) Raw - Plan: '{user.plan_prefer}', Vibe: '{user.vibe_prefer}', Places: '{user.places_prefer}', Extras: '{user.extra_prefer1}', '{user.extra_prefer2}', '{user.extra_prefer3}'")
    
    inputs = TravelState(
        user_input=message_in.message,
        user_id=user.id,
        room_id=room.id,
        latitude=message_in.latitude,
        longitude=message_in.longitude,
        image_path=message_in.image_path,
        prefs_info=user.build_preferences(),
        messages=[HumanMessage(content=message_in.message)],
        summary_title=room.title,
        summary_message=room.history,
    )
    print(f"[BuildInputs] Prefs info built: {inputs['prefs_info']}")
    return inputs

# 채팅방 목록 조회
@router.get("/rooms", response_model=List[ChatRoomResponse])
def get_rooms(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    rooms = (
        db.query(ChatRoom)
        .filter(ChatRoom.user_id == current_user.id)
        .order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rooms


@router.get("/recommendations/today", response_model=List[TodayRecommendationItem])
def get_today_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    rooms_with_history = (
        db.query(ChatRoom)
        .filter(ChatRoom.user_id == current_user.id)
        .filter(ChatRoom.history.isnot(None))
        .filter(func.length(func.trim(ChatRoom.history)) > 0)
        .order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
        .limit(5)
        .all()
    )

    if not rooms_with_history:
        return []

    latest_room = rooms_with_history[0]
    latest_history = _clean_history_text(latest_room.history or "")
    latest_title = latest_room.title.strip() if latest_room and latest_room.title else "최근 여행 대화"
    latest_snippet = _shorten_text(latest_history, 56)

    recent_histories: List[str] = []
    for room in rooms_with_history:
        text = _clean_history_text(room.history or "")
        if text:
            recent_histories.append(text)

    uniq_histories: List[str] = []
    for text in recent_histories:
        if text not in uniq_histories:
            uniq_histories.append(text)

    first_theme = _shorten_text(uniq_histories[0], 52) if uniq_histories else latest_snippet
    second_theme = _shorten_text(uniq_histories[1], 52) if len(uniq_histories) > 1 else first_theme

    continue_title = f"Continue: {latest_title}"
    continue_desc = "최근 대화 맥락을 이어서 바로 다음 계획으로 확장해보세요."
    continue_prompt = (
        f"다음은 최근 대화 요약입니다: {latest_history}\n"
        "기존 맥락을 이어 하루 단위로 실행 가능한 여행 계획을 제안해줘."
    )

    new_angle_title = "Try a new angle"
    new_angle_desc = f"최근 대화 주제와 다른 관점으로 새 플랜을 제안합니다: {second_theme}"
    new_angle_prompt = (
        "다음 최근 대화 요약들을 참고해 기존과 다른 각도의 여행 아이디어를 1개 제안해줘.\n"
        + "\n".join([f"- {h}" for h in uniq_histories[:3]])
        + "\n새 아이디어는 이동 동선과 핵심 포인트를 포함해 간결하게 작성해줘."
    )

    quick_plan_title = "Fast plan for today"
    quick_plan_desc = f"최근 요약 기반으로 바로 실행 가능한 짧은 일정: {first_theme}"
    quick_plan_prompt = (
        f"최근 대화 요약: {latest_history}\n"
        "오늘 바로 실행할 수 있는 3스팟 반나절 일정(순서/이동/예상시간 포함)을 간단히 제시해줘."
    )

    return [
        TodayRecommendationItem(
            id="continue",
            title=continue_title,
            description=continue_desc,
            prompt=continue_prompt,
        ),
        TodayRecommendationItem(
            id="new-angle",
            title=new_angle_title,
            description=new_angle_desc,
            prompt=new_angle_prompt,
        ),
        TodayRecommendationItem(
            id="fast-plan",
            title=quick_plan_title,
            description=quick_plan_desc,
            prompt=quick_plan_prompt,
        ),
    ]

# 채팅방 생성
@router.post("/rooms", response_model=ChatRoomResponse)
def create_room(room_in: ChatRoomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    new_room = ChatRoom(user_id=current_user.id, title=room_in.title)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

# 채팅방 상세 조회 (대화 내역 포함)
@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
def get_room_history(room_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    room = db.query(ChatRoom).options(
        joinedload(ChatRoom.messages).joinedload(ChatMessage.places)
    ).filter(ChatRoom.id == room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND, "Room not found", 404)
    for message in room.messages:
        if message.image_path:
            message.image_path = to_client_image_url(message.image_path)
        for place in message.places:
            place.image_path = to_client_image_url(place.image_path)
    return room


@router.patch("/rooms/{room_id}/bookmark", response_model=ChatRoomResponse)
def update_room_bookmark(room_id: int, bookmark: bool, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id,
        ChatRoom.user_id == current_user.id,
    ).first()

    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND_OR_DENIED, "Room not found or permission denied", 404)

    room.bookmark_yn = bookmark
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

# 메시지 저장
@router.post("/messages", response_model=ChatMessageResponse)
def create_message(message_in: ChatMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    # 채팅방 소유권 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == message_in.room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND_OR_DENIED, "Room not found or permission denied", 404)

    new_message = ChatMessage(
        room_id=message_in.room_id,
        message=message_in.message,
        role=message_in.role,
        latitude=_input_coordinate_or_none(message_in.latitude),
        longitude=_input_coordinate_or_none(message_in.longitude),
        image_path=message_in.image_path,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


# 추천 장소 북마크 업데이트
@router.patch("/places/{place_id}/bookmark", response_model=ChatPlaceResponse)
def update_place_bookmark(place_id: int, bookmark: bool, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    # 장소를 찾고, 해당 메시지의 세션 소유자가 현재 사용자인지 확인 (조인 필요)
    place = db.query(ChatPlace).join(ChatMessage).join(ChatRoom).filter(
        ChatPlace.id == place_id,
        ChatRoom.user_id == current_user.id
    ).first()
    
    if not place:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Place not found or permission denied", 404)
    
    place.bookmark_yn = bookmark
    
    db.add(place)
    db.commit()
    db.refresh(place)
    place.image_path = to_client_image_url(place.image_path)
    return place


@router.get("/bookmarks/rooms", response_model=List[BookmarkedRoomResponse])
def get_bookmarked_rooms(current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    latest_message_subquery = (
        db.query(
            ChatMessage.room_id.label("room_id"),
            func.max(ChatMessage.id).label("latest_message_id"),
        )
        .group_by(ChatMessage.room_id)
        .subquery()
    )
    latest_message_alias = aliased(ChatMessage)

    rows = (
        db.query(ChatRoom, latest_message_alias.message.label("latest_message_preview"))
        .outerjoin(latest_message_subquery, latest_message_subquery.c.room_id == ChatRoom.id)
        .outerjoin(latest_message_alias, latest_message_alias.id == latest_message_subquery.c.latest_message_id)
        .filter(
            ChatRoom.user_id == current_user.id,
            ChatRoom.bookmark_yn.is_(True),
        )
        .order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
        .all()
    )

    return [
        {
            "id": room.id,
            "user_id": room.user_id,
            "title": room.title or "새 채팅",
            "created_at": room.created_at,
            "bookmark_yn": room.bookmark_yn,
            "latest_message_preview": latest_message_preview,
        }
        for room, latest_message_preview in rows
    ]


@router.get("/bookmarks/places", response_model=List[BookmarkedPlaceResponse])
def get_bookmarked_places(current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    rows = (
        db.query(ChatPlace, ChatMessage.room_id, ChatRoom.title)
        .join(ChatMessage, ChatMessage.id == ChatPlace.messages_id)
        .join(ChatRoom, ChatRoom.id == ChatMessage.room_id)
        .filter(
            ChatRoom.user_id == current_user.id,
            ChatPlace.bookmark_yn.is_(True),
        )
        .order_by(ChatPlace.id.desc())
        .all()
    )

    return [
        {
            "id": place.id,
            "place_id": _normalize_int_or_zero(place.place_id),
            "name": place.name,
            "adress": place.adress,
            "image_path": to_client_image_url(place.image_path),
            "longitude": _normalize_float_or_zero(place.longitude),
            "latitude": _normalize_float_or_zero(place.latitude),
            "bookmark_yn": place.bookmark_yn,
            "messages_id": place.messages_id,
            "room_id": room_id,
            "room_title": room_title or "새 채팅",
        }
        for place, room_id, room_title in rows
    ]



# 대화하기 (User Message 저장 -> LLM 생성 -> AI Message 저장 -> 반환)
@router.post("/rooms/{room_id}/ask", response_model=ChatMessageResponse)
async def ask_chat(room_id: int, message_in: ChatMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(db_manager.get_db)):
    room = _get_owned_room_or_404(db, room_id, current_user.id)
    _save_human_message_if_needed(db, room_id, message_in)
    should_update_title = _should_update_room_title(db, room_id)

    # 그래프 입력 상태 구성 (대화 이력은 checkpointer가 자동 관리)
    inputs = _build_graph_inputs(current_user, room, message_in)
    
    # 그래프 실행 (Global Cache)
    try:
        print(f"[ChatAPI] Starting graph invocation for room_id={room_id}")
        config = {"configurable": {"thread_id": f"room_{room_id}"}}
        graph_app = await get_graph_app()
        result = await graph_app.ainvoke(inputs, config=config)
        print(f"[ChatAPI] Graph invocation completed for room_id={room_id}")
        ai_reply_text = result.get("answer", "죄송합니다. 답변을 생성하지 못했습니다.")
        
        if should_update_title and _can_overwrite_room_title(room):
            # 방 제목 자동 설정 (메시지 2개 이하일 때만)
            title = result.get("summary_title")
            fallback_message = message_in.message
            next_title = title if title else fallback_message
            _save_room_title(db, room, next_title)
    except Exception as e:
        print(f"[ChatAPI] Graph Execution Error in room_id {room_id}: {e}")
        import traceback
        traceback.print_exc()
        ai_reply_text = "죄송합니다. 오류가 발생했습니다."
    
    # AI Message 저장
    ai_message = ChatMessage(
        room_id=room_id,
        message=ai_reply_text,
        role=RoleType.ai,
        image_path=None, # AI가 이미지를 생성한다면 여기 추가
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    
    return ai_message


def _build_streaming_response(
    room_id: int,
    room: ChatRoom,
    message_in: ChatMessageCreate,
    current_user: User,
    db: Session,
) -> StreamingResponse:
    _save_human_message_if_needed(db, room_id, message_in)
    should_update_title = _should_update_room_title(db, room_id)
    inputs = _build_graph_inputs(current_user, room, message_in)
    config = {"configurable": {"thread_id": f"room_{room_id}"}}

    async def event_generator():
        full_answer = ""
        streamed_visible_text = ""
        in_executor = False  # executor 노드 안에서만 LLM 토큰 전송
        selected_ids = []
        candidates = []

        def _chunk_to_text(chunk) -> str:
            if chunk is None:
                return ""
            if isinstance(chunk, dict):
                text = chunk.get("text")
                if isinstance(text, str):
                    return text
                content = chunk.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = []
                    for part in content:
                        if isinstance(part, dict):
                            t = part.get("text")
                            if t:
                                texts.append(str(t))
                        elif isinstance(part, str):
                            texts.append(part)
                    return "".join(texts)
            if hasattr(chunk, "content"):
                content = getattr(chunk, "content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = []
                    for part in content:
                        if isinstance(part, dict):
                            t = part.get("text")
                            if t:
                                texts.append(str(t))
                        elif isinstance(part, str):
                            texts.append(part)
                    return "".join(texts)
            if hasattr(chunk, "text"):
                text = getattr(chunk, "text")
                if isinstance(text, str):
                    return text
            if isinstance(chunk, str):
                return chunk
            return ""
        try:
            graph_app = await get_graph_app()
            # 그래프에서 노드 이름을 동적으로 가져옴 (__start__, __end__ 등 내부 노드 제외)
            graph_nodes = {name for name in graph_app.nodes if not name.startswith("__")}
            async for event in graph_app.astream_events(inputs, config=config, version="v2"):
                kind = event.get("event", "")
                name = event.get("name", "")

                # 노드 시작/종료 이벤트
                if kind == "on_chain_start" and name in graph_nodes:
                    yield f"data: {json.dumps({'step': name, 'status': 'start'})}\n\n"
                    if name in ("executor", "executor_missing"):
                        in_executor = True
                elif kind == "on_chain_end" and name in graph_nodes:
                    yield f"data: {json.dumps({'step': name, 'status': 'done'})}\n\n"
                    
                    output = event.get("data", {}).get("output", {})
                    print(f"[SSE] Node '{name}' finished. Output keys: {list(output.keys())}")
                    
                    if name in ("executor", "executor_missing"):
                        in_executor = False
                        # executor 노드 종료 시 결과 캡처
                        output = event.get("data", {}).get("output", {})
                        if "selected_ids" in output:
                            selected_ids = output["selected_ids"]
                            print(f"[SSE] Captured selected_ids: {selected_ids}")
                        if "answer" in output:
                            full_answer = output["answer"]
                    
                    if name == "retriever":
                        output = event.get("data", {}).get("output", {})
                        if "candidates" in output:
                            candidates = output["candidates"]
                            print(f"[SSE] Captured {len(candidates)} candidates")
                    
                    # Intent 노드 종료 시점에 summary_title 제목 즉시 업데이트
                    if name == "intent":
                        output = event.get("data", {}).get("output")
                        if should_update_title and output and _can_overwrite_room_title(room):
                            summary_title = output.get("summary_title")
                            fallback_message = message_in.message
                            next_title = summary_title if summary_title else fallback_message
                            if _save_room_title(db, room, next_title):
                                print(f"[ChatAPI] Room title updated to: {room.title}")
                                # 프론트엔드에 제목 즉시 전송 (done 이벤트 기다리지 않음)
                                yield f"data: {json.dumps({'room_title': room.title})}\n\n"

                # LLM 토큰 스트리밍 (executor 노드의 LLM만)
                elif kind in ("on_chat_model_stream", "on_llm_stream") and in_executor:
                    chunk = event.get("data", {}).get("chunk")
                    token_text = _chunk_to_text(chunk)
                    if token_text:
                        full_answer += token_text

                        # [IDs: ...] 태그(완성/미완성)를 모두 숨긴 가시 텍스트 계산
                        visible_text = re.sub(r"\[IDs:\s*.*?\]", "", full_answer, flags=re.DOTALL)
                        partial_tag_start = visible_text.rfind("[IDs:")
                        if partial_tag_start != -1:
                            visible_text = visible_text[:partial_tag_start]

                        if len(visible_text) > len(streamed_visible_text):
                            delta = visible_text[len(streamed_visible_text):]
                            streamed_visible_text = visible_text
                            if delta:
                                yield f"data: {json.dumps({'token': delta})}\n\n"
                        else:
                            # 태그 완성 시 텍스트 길이가 줄어들 수 있으므로 기준만 동기화
                            streamed_visible_text = visible_text


        except asyncio.CancelledError:
            db.rollback()
            print(f"[ChatAPI] Stream cancelled in room_id {room_id}")
            raise
        except Exception as e:
            print(f"[ChatAPI] Stream error in room_id {room_id}: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            if not full_answer:
                full_answer = "죄송합니다. 오류가 발생했습니다."
                yield f"data: {json.dumps({'token': full_answer})}\n\n"

        # AI 메시지 DB 저장
        if not full_answer:
            full_answer = "죄송합니다. 답변을 생성하지 못했습니다."

        ai_message = ChatMessage(
            room_id=room_id,
            message=full_answer,
            role=RoleType.ai,
            image_path=None,
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        # ChatPlace 저장 및 반환용 리스트 구성
        final_places = []
        if candidates:
            def _normalize_text(value: str) -> str:
                return re.sub(r"\s+", "", (value or "")).lower()

            def _candidate_id(candidate: dict) -> str:
                payload = candidate.get("payload", {}) or {}
                return str(payload.get("contentid") or candidate.get("id") or "").strip()

            def _infer_candidates_from_answer(answer_text: str):
                if not answer_text:
                    return []
                inferred = []
                link_names = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", answer_text)
                for raw_name in link_names:
                    name_key = _normalize_text(raw_name)
                    candidate = next(
                        (
                            c for c in candidates
                            if _normalize_text((c.get("payload", {}) or {}).get("title") or (c.get("payload", {}) or {}).get("name") or "")
                            and (
                                name_key in _normalize_text((c.get("payload", {}) or {}).get("title") or (c.get("payload", {}) or {}).get("name") or "")
                                or _normalize_text((c.get("payload", {}) or {}).get("title") or (c.get("payload", {}) or {}).get("name") or "") in name_key
                            )
                        ),
                        None,
                    )
                    if candidate and candidate not in inferred:
                        inferred.append(candidate)
                return inferred

            # 우선순위: LLM이 선택한 ID 순서 -> 답변 링크/이름 매칭
            ordered_candidates = []
            if selected_ids:
                for cid in selected_ids:
                    candidate = next((c for c in candidates if _candidate_id(c) == str(cid).strip()), None)
                    if candidate and candidate not in ordered_candidates:
                        ordered_candidates.append(candidate)

            if not ordered_candidates:
                cleaned_for_match = re.sub(r"\[\s*ids?\s*:\s*.*?\]", "", full_answer, flags=re.IGNORECASE).strip()
                ordered_candidates = _infer_candidates_from_answer(cleaned_for_match)

            for candidate in ordered_candidates[:3]:
                payload = candidate.get("payload", {})
                candidate_pid = _candidate_id(candidate)
                new_place = ChatPlace(
                    messages_id=ai_message.id,
                    place_id=int(candidate_pid) if candidate_pid.isdigit() else 0,
                    name=payload.get("title") or payload.get("name"),
                    adress=payload.get("address") or payload.get("addr") or payload.get("road_address"),
                    image_path=(
                        payload.get("image")
                        or payload.get("image_url")
                        or payload.get("firstimage")
                        or payload.get("firstimage2")
                    ),
                    longitude=_normalize_float_or_zero(payload.get("mapx")),
                    latitude=_normalize_float_or_zero(payload.get("mapy")),
                    bookmark_yn=False
                )
                db.add(new_place)
                final_places.append(new_place)
            db.commit()
            for p in final_places:
                db.refresh(p)

        # SSE 응답 스키마에 맞게 변환
        places_data = [
            {
                "id": p.id,
                "place_id": _normalize_int_or_zero(p.place_id),
                "name": p.name,
                "adress": p.adress,
                "image_path": to_client_image_url(p.image_path),
                "longitude": _normalize_float_or_zero(p.longitude),
                "latitude": _normalize_float_or_zero(p.latitude),
                "bookmark_yn": p.bookmark_yn
            } for p in final_places
        ]
        
        print(f"[SSE] Sending 'done' event with {len(places_data)} places")
        yield f"data: {json.dumps({'done': True, 'full_message': full_answer, 'message_id': ai_message.id, 'created_at': ai_message.created_at.isoformat(), 'room_title': room.title, 'places': places_data})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# 대화하기 — SSE 스트리밍
@router.post("/rooms/{room_id}/ask/stream")
async def ask_chat_stream(
    room_id: int,
    message_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    room = _get_owned_room_or_404(db, room_id, current_user.id)
    return _build_streaming_response(room_id, room, message_in, current_user, db)


@router.post("/rooms/{room_id}/autostart/stream")
async def auto_start_chat_room_stream(
    room_id: int,
    auto_start_in: AutoStartChatRoomRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_manager.get_db),
):
    room = _get_owned_room_or_404(db, room_id, current_user.id)

    if auto_start_in.mode == "trip_context":
        if auto_start_in.trip_context is None:
            raise AppException(ErrorCode.VALIDATION_ERROR, "trip_context is required for mode=trip_context", 400)
        prompt = render_auto_start_prompt(
            travel_duration=auto_start_in.trip_context.travel_duration,
            adult_count=auto_start_in.trip_context.adult_count,
            child_count=auto_start_in.trip_context.child_count,
        )
    elif auto_start_in.mode == "selected_places":
        if not auto_start_in.selected_places:
            raise AppException(ErrorCode.VALIDATION_ERROR, "selected_places is required for mode=selected_places", 400)
        prompt = render_auto_start_place_prompt(auto_start_in.selected_places)
    elif auto_start_in.mode == "combined":
        if auto_start_in.trip_context is None:
            raise AppException(ErrorCode.VALIDATION_ERROR, "trip_context is required for mode=combined", 400)
        if not auto_start_in.selected_places:
            raise AppException(ErrorCode.VALIDATION_ERROR, "selected_places is required for mode=combined", 400)
        prompt = render_auto_start_combined_prompt(
            travel_duration=auto_start_in.trip_context.travel_duration,
            adult_count=auto_start_in.trip_context.adult_count,
            child_count=auto_start_in.trip_context.child_count,
            selected_places=auto_start_in.selected_places,
        )
    elif auto_start_in.mode == "greeting":
        prompt = render_auto_start_greeting_prompt()
    else:
        raise AppException(ErrorCode.VALIDATION_ERROR, "Unsupported auto start mode", 400)

    message_in = ChatMessageCreate(
        room_id=room_id,
        message=prompt,
        role=RoleType.human,
        save_user_message=auto_start_in.save_user_message,
    )
    return _build_streaming_response(room_id, room, message_in, current_user, db)
