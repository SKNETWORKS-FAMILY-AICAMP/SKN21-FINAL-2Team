"""
SSE 스트리밍 엔드포인트 (/rooms/{room_id}/ask/stream) 자동 테스트

LLM과 그래프는 mock 처리하여 외부 의존 없이 테스트합니다.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.connection import get_db, Base
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from app.utils.security import create_access_token

# ---------- fixtures ----------

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_db(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def user_and_room(override_db):
    """테스트용 사용자와 채팅방 생성"""
    db = override_db
    user = User(email="stream@test.com", name="StreamUser")
    db.add(user)
    db.commit()
    db.refresh(user)

    room = ChatRoom(user_id=user.id, title="Test Room")
    db.add(room)
    db.commit()
    db.refresh(room)

    token = create_access_token(user.email)
    return user, room, token, db


# ---------- 모킹 헬퍼 ----------

async def _mock_astream_events(*args, **kwargs):
    """LangGraph astream_events를 모킹 — 노드 이벤트 + LLM 토큰"""
    # intent 노드
    yield {"event": "on_chain_start", "name": "intent", "data": {}}
    yield {"event": "on_chain_end", "name": "intent", "data": {}}

    # retriever 노드
    yield {"event": "on_chain_start", "name": "retriever", "data": {}}
    yield {"event": "on_chain_end", "name": "retriever", "data": {}}

    # executor 노드
    yield {"event": "on_chain_start", "name": "executor", "data": {}}

    # LLM 토큰 스트리밍
    for token_text in ["안녕", "하세요", "! 여행을 ", "도와드릴게요."]:
        chunk = MagicMock()
        chunk.content = token_text
        yield {"event": "on_chat_model_stream", "name": "ChatOpenAI", "data": {"chunk": chunk}}

    yield {"event": "on_chain_end", "name": "executor", "data": {}}


def _get_mock_graph_app():
    mock_app = AsyncMock()
    mock_app.astream_events = _mock_astream_events
    return mock_app


# ---------- 테스트 ----------

@pytest.mark.asyncio
async def test_sse_event_format(user_and_room):
    """SSE 라인이 'data: {...}\\n\\n' 형식인지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "제주도 여행 추천해줘", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            lines = response.text.strip().split("\n\n")
            for line in lines:
                assert line.startswith("data: "), f"Expected 'data: ' prefix, got: {line}"
                payload = json.loads(line[6:])
                assert isinstance(payload, dict)


@pytest.mark.asyncio
async def test_step_events_order(user_and_room):
    """노드 step 이벤트가 올바른 순서로 발생하는지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )

            step_events = []
            for line in response.text.strip().split("\n\n"):
                data = json.loads(line[6:])
                if "step" in data:
                    step_events.append((data["step"], data["status"]))

            # intent → retriever → executor 순서 확인
            step_names = [s[0] for s in step_events if s[1] == "start"]
            assert step_names == ["intent", "retriever", "executor"]


@pytest.mark.asyncio
async def test_token_streaming(user_and_room):
    """token 이벤트가 1개 이상 수신되는지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )

            token_events = []
            for line in response.text.strip().split("\n\n"):
                data = json.loads(line[6:])
                if "token" in data:
                    token_events.append(data["token"])

            assert len(token_events) >= 1
            full_text = "".join(token_events)
            assert "안녕하세요" in full_text


@pytest.mark.asyncio
async def test_done_event_with_message_id(user_and_room):
    """마지막 이벤트에 done=True와 message_id가 포함되는지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )

            lines = response.text.strip().split("\n\n")
            last_data = json.loads(lines[-1][6:])

            assert last_data.get("done") is True
            assert "message_id" in last_data
            assert isinstance(last_data["message_id"], int)


@pytest.mark.asyncio
async def test_ai_message_saved_to_db(user_and_room):
    """스트리밍 완료 후 DB에 AI 메시지가 저장되었는지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "DB 저장 테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )

    # DB에서 AI 메시지 확인
    ai_messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.role == "ai",
    ).all()

    assert len(ai_messages) == 1
    assert "안녕하세요" in ai_messages[0].message
