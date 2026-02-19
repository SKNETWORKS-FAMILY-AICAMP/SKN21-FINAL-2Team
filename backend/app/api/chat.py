import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from app.models.enums import RoleType
from app.schemas.chat import ChatRoomCreate, ChatRoomResponse, ChatMessageCreate, ChatMessageResponse
from app.core.security import get_current_user
from app.agents.graph import workflow
from app.database.checkpointer import get_checkpointer

from langchain_core.messages import HumanMessage

_graph_app = None
_checkpointer = None

async def get_graph_app():
    global _graph_app, _checkpointer
    if _graph_app is None:
        print('init graph app')
        _checkpointer = await get_checkpointer()
        _graph_app = workflow().compile(checkpointer=_checkpointer)
        print('compile graph app (with AsyncMySaver checkpointer)')
    return _graph_app


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
        raise HTTPException(status_code=404, detail="Room not found")
    return room

# 메시지 저장
@router.post("/messages", response_model=ChatMessageResponse)
def create_message(message_in: ChatMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 채팅방 소유권 확인
    room = db.query(ChatRoom).filter(ChatRoom.id == message_in.room_id, ChatRoom.user_id == current_user.id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or permission denied")

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
        raise HTTPException(status_code=404, detail="Message not found or permission denied")
    
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
        raise HTTPException(status_code=404, detail="Room not found")

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
    
    # 방 제목 자동 설정 (없거나 기본값일 때)
    if not room.title or room.title.lower() == "new chat":
        room.title = _make_room_title(message_in.message)
        db.add(room)
        db.commit()

    # 그래프 입력 상태 구성 (대화 이력은 checkpointer가 자동 관리)
    inputs = {
        "user_input": message_in.message,
        "user_id": current_user.id,
        "room_id": room_id,
        "latitude": message_in.latitude,
        "longitude": message_in.longitude,
        "image_path": message_in.image_path,
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
