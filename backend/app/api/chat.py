import re
import json
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from app.models.enums import RoleType
from app.schemas.chat import ChatRoomCreate, ChatRoomResponse, ChatMessageCreate, ChatMessageResponse
from app.utils.security import get_current_user
from app.utils.error_handler import AppException, ErrorCode
from app.agents.graph import workflow
from app.database.checkpointer import get_checkpointer

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


def _build_user_preferences(user: User) -> str:
    """
    DB의 사용자 정보를 기반으로 선호도 텍스트를 생성합니다.
    LLM Agent에 전달할 prefs_info 문자열을 반환합니다.
    """
    if not user:
        return "특별한 선호도 정보 없음"

    lines = []

    if user.plan_prefer:
        lines.append(f"- 📋 여행 일정 스타일: **{user.plan_prefer}**")
    if user.vibe_prefer:
        lines.append(f"- ✨ 선호 여행 환경: **{user.vibe_prefer}**")
    if user.places_prefer:
        lines.append(f"- � 관심 장소 유형: **{user.places_prefer}**")

    return "\n".join(lines) if lines else "특별한 선호도 정보 없음"


router = APIRouter(prefix="/api/chat", tags=["chat"])

def _make_room_title(text: str) -> str:
    """Generate a concise room title from user input."""
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if len(clean) > 30:
        clean = clean[:30].rstrip() + "..."
    return clean or "새 채팅"

# 채팅방 목록 조회
@router.get("/rooms", response_model=List[ChatRoomResponse])
def get_rooms(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rooms = (
        db.query(ChatRoom)
        .filter(ChatRoom.user_id == current_user.id)
        .order_by(ChatRoom.created_at.desc(), ChatRoom.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rooms

# 채팅방 생성
@router.post("/rooms", response_model=ChatRoomResponse)
def create_room(room_in: ChatRoomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_room = ChatRoom(user_id=current_user.id, title=room_in.title)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

# 채팅방 상세 조회 (대화 내역 포함)
@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
def get_room_history(room_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND, "Room not found", 404)
    return room

# 메시지 저장
@router.post("/messages", response_model=ChatMessageResponse)
def create_message(message_in: ChatMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 채팅방 소유권 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == message_in.room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND_OR_DENIED, "Room not found or permission denied", 404)

    new_message = ChatMessage(
        room_id=message_in.room_id,
        message=message_in.message,
        role=message_in.role,
        latitude=message_in.latitude,
        longitude=message_in.longitude,
        image_path=message_in.image_path,
        bookmark_yn=message_in.bookmark_yn
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message

# 북마크 업데이트
@router.patch("/messages/{message_id}/bookmark", response_model=ChatMessageResponse)
def update_bookmark(message_id: int, bookmark: bool, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 메시지를 찾고, 해당 메시지의 세션 소유자가 현재 사용자인지 확인 (조인 필요)
    message = db.query(ChatMessage).join(ChatRoom).filter(
        ChatMessage.id == message_id,
        ChatRoom.user_id == current_user.id
    ).first()
    
    if not message:
        raise AppException(ErrorCode.CHAT_MESSAGE_NOT_FOUND_OR_DENIED, "Message not found or permission denied", 404)
    
    message.bookmark_yn = bookmark
    
    db.add(message)
    db.commit()
    db.refresh(message)
    return message



# 대화하기 (User Message 저장 -> LLM 생성 -> AI Message 저장 -> 반환)
@router.post("/rooms/{room_id}/ask", response_model=ChatMessageResponse)
async def ask_chat(room_id: int, message_in: ChatMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 채팅방 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND, "Room not found", 404)

    # User Message 저장
    user_message = ChatMessage(
        room_id=room_id,
        message=message_in.message,
        role=RoleType.human, # 강제 설정
        latitude=message_in.latitude,
        longitude=message_in.longitude,
        image_path=message_in.image_path,
        bookmark_yn=False
    )
    db.add(user_message)
    db.commit()
    
    # 방 제목 자동 설정 (초기값인 경우에만)
    # 아래 graph_app.ainvoke 결과에서 summary_query를 받아와서 업데이트하도록 이동

    # Backend에서 사용자 선호도 조회 후 LLM에 전달
    prefs_info = _build_user_preferences(current_user)

    # 그래프 입력 상태 구성 (대화 이력은 checkpointer가 자동 관리)
    inputs = {
        "user_input": message_in.message,
        "user_id": current_user.id,
        "room_id": room_id,
        "latitude": message_in.latitude,
        "longitude": message_in.longitude,
        "image_path": message_in.image_path,
        "prefs_info": prefs_info,
        "messages": [HumanMessage(content=message_in.message)],
    }

    
    # 그래프 실행 (Global Cache)
    try:
        print(f"[ChatAPI] Starting graph invocation for room_id={room_id}")
        config = {"configurable": {"thread_id": f"room_{room_id}"}}
        graph_app = await get_graph_app()
        result = await graph_app.ainvoke(inputs, config=config)
        print(f"[ChatAPI] Graph invocation completed for room_id={room_id}")
        ai_reply_text = result.get("answer", "죄송합니다. 답변을 생성하지 못했습니다.")
        
        # 방 제목 자동 설정 (기본값인 경우에만 요약된 제목으로 업데이트)
        summary_query = result.get("summary_query")
        if summary_query and (not room.title or room.title == "새로운 여행 계획"):
            room.title = summary_query
            db.add(room)
            db.commit()
            db.refresh(room)
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
        bookmark_yn=False
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    
    return ai_message




# 대화하기 — SSE 스트리밍
@router.post("/rooms/{room_id}/ask/stream")
async def ask_chat_stream(
    room_id: int,
    message_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 채팅방 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise AppException(ErrorCode.CHAT_ROOM_NOT_FOUND, "Room not found", 404)

    # User Message 저장
    user_message = ChatMessage(
        room_id=room_id,
        message=message_in.message,
        role=RoleType.human,
        latitude=message_in.latitude,
        longitude=message_in.longitude,
        image_path=message_in.image_path,
        bookmark_yn=False,
    )
    db.add(user_message)
    db.commit()

    # 방 제목 자동 설정 로직은 스트림 이벤트를 통해 처리하도록 이동

    # 사용자 선호도
    prefs_info = _build_user_preferences(current_user)

    inputs = {
        "user_input": message_in.message,
        "user_id": current_user.id,
        "room_id": room_id,
        "latitude": message_in.latitude,
        "longitude": message_in.longitude,
        "image_path": message_in.image_path,
        "prefs_info": prefs_info,
        "messages": [HumanMessage(content=message_in.message)],
    }
    config = {"configurable": {"thread_id": f"room_{room_id}"}}

    async def event_generator():
        full_answer = ""
        in_executor = False  # executor 노드 안에서만 LLM 토큰 전송
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
                    if name in ("executor", "executor_missing"):
                        in_executor = False
                    
                    # Intent 노드 종료 시점에 summary_query로 제목 즉시 업데이트
                    if name == "intent":
                        output = event.get("data", {}).get("output")
                        if output and "summary_query" in output:
                            summary_query = output["summary_query"]
                            if summary_query and (not room.title or room.title == "새로운 여행 계획"):
                                room.title = summary_query
                                db.add(room)
                                db.commit()
                                db.refresh(room)
                                print(f"[ChatAPI] Room title updated to: {summary_query}")
                                # 프론트엔드에 제목 즉시 전송 (done 이벤트 기다리지 않음)
                                yield f"data: {json.dumps({'room_title': room.title})}\n\n"

                # LLM 토큰 스트리밍 (executor 노드의 LLM만)
                elif kind == "on_chat_model_stream" and in_executor:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        full_answer += chunk.content
                        yield f"data: {json.dumps({'token': chunk.content})}\n\n"


        except Exception as e:
            print(f"[ChatAPI] Stream error in room_id {room_id}: {e}")
            import traceback
            traceback.print_exc()
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
            bookmark_yn=False,
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        yield f"data: {json.dumps({'done': True, 'message_id': ai_message.id, 'created_at': ai_message.created_at.isoformat(), 'room_title': room.title})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
