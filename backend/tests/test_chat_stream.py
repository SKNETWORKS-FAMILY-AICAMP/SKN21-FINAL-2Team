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
from app.database.connection import Base, db_manager
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage, ChatPlace
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

    app.dependency_overrides[db_manager.get_db] = _override
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
    yield {
        "event": "on_chain_end",
        "name": "intent",
        "data": {"output": {"summary_title": "요약된 제목", "summary_message": "요약 메시지 제목"}},
    }

    # retriever 노드
    yield {"event": "on_chain_start", "name": "retriever", "data": {}}
    yield {"event": "on_chain_end", "name": "retriever", "data": {"output": {"candidates": [{"payload": {"contentid": "123", "title": "Test Place", "address": "Test Address"}}]}}}

    # executor 노드
    yield {"event": "on_chain_start", "name": "executor", "data": {}}

    # executor custom token 스트리밍
    for token_text in ["안녕", "하세요", "! 여행을 ", "도와드릴게요."]:
        yield {"event": "on_custom_event", "name": "token", "data": {"token": token_text}}

    yield {"event": "on_chain_end", "name": "executor", "data": {"output": {"answer": "추천 답변입니다.", "selected_ids": ["123"]}}}


def _get_mock_graph_app():
    mock_app = AsyncMock()
    mock_app.astream_events = _mock_astream_events
    mock_app.nodes = {"intent": None, "planner": None, "retriever": None, "executor": None, "executor_missing": None}
    return mock_app


def _extract_data_payloads(response_text: str) -> list[dict]:
    payloads: list[dict] = []
    for raw_event in response_text.strip().split("\n\n"):
        data_lines = [
            line[6:]
            for line in raw_event.split("\n")
            if line.startswith("data: ")
        ]
        if not data_lines:
            continue
        payloads.append(json.loads("\n".join(data_lines)))
    return payloads


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

            payloads = _extract_data_payloads(response.text)
            assert payloads, "Expected at least one SSE data payload"
            for payload in payloads:
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
            for data in _extract_data_payloads(response.text):
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
            for data in _extract_data_payloads(response.text):
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
            assert "room_title" in last_data

@pytest.mark.asyncio
async def test_room_title_updated_to_summary(user_and_room):
    """초기 2개 메시지 구간에서는 summary_title로 제목을 갱신한다."""
    user, room, token, db = user_and_room
    # 초기 제목 설정
    room.title = "새로운 여행 계획"
    db.add(room)
    db.commit()

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )
            
            # DB에서 제목 확인
            db.refresh(room)
            assert room.title == "요약된 제목"
            
            # 마지막 이벤트에서도 확인
            lines = response.text.strip().split("\n\n")
            last_data = json.loads(lines[-1][6:])
            assert last_data["room_title"] == "요약된 제목"


@pytest.mark.asyncio
async def test_stream_does_not_overwrite_custom_title_even_within_first_two_messages(user_and_room):
    user, room, token, db = user_and_room
    room.title = "내가 정한 제목"
    db.add(room)
    db.commit()

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    db.refresh(room)
    assert room.title == "내가 정한 제목"


@pytest.mark.asyncio
async def test_room_title_not_updated_when_message_count_exceeds_two(user_and_room):
    """메시지 수가 3개 이상이면 제목 자동 갱신을 하지 않는다."""
    user, room, token, db = user_and_room

    room.title = "유지 제목"
    db.add(room)
    db.commit()

    db.add_all([
        ChatMessage(room_id=room.id, message="m1", role="human"),
        ChatMessage(room_id=room.id, message="m2", role="ai"),
    ])
    db.commit()

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "m3", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    db.refresh(room)
    assert room.title == "유지 제목"


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
    assert "추천 답변입니다" in ai_messages[0].message


@pytest.mark.asyncio
async def test_stream_skip_user_message_save(user_and_room):
    """save_user_message=False면 human 메시지를 DB에 저장하지 않는다."""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "자동 시작", "role": "human", "save_user_message": False},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    human_messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.role == "human",
    ).all()
    ai_messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.role == "ai",
    ).all()

    assert len(human_messages) == 0
    assert len(ai_messages) == 1


@pytest.mark.asyncio
async def test_chat_place_saved_with_message(user_and_room):
    """스트리밍 완료 후 ChatPlace가 저장되었는지 확인"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/ask/stream",
                json={"room_id": room.id, "message": "장소 저장 테스트", "role": "human"},
                headers={"Authorization": f"Bearer {token}"},
            )
            
            last_line = response.text.strip().split("\n\n")[-1]
            data = json.loads(last_line[6:])
            assert "places" in data
            assert len(data["places"]) == 1
            assert data["places"][0]["name"] == "Test Place"
            assert data["places"][0]["longitude"] == 0.0
            assert data["places"][0]["latitude"] == 0.0

    # DB 확인
    from app.models.chat import ChatPlace
    places = db.query(ChatPlace).join(ChatMessage).filter(ChatMessage.room_id == room.id).all()
    assert len(places) == 1
    assert places[0].name == "Test Place"


@pytest.mark.asyncio
async def test_update_place_bookmark(user_and_room):
    """ChatPlace 북마크 PATCH API 동작 확인"""
    user, room, token, db = user_and_room
    
    # 더미 메시지 및 장소 생성
    msg = ChatMessage(room_id=room.id, message="test", role="ai")
    db.add(msg)
    db.commit()
    
    place = ChatPlace(messages_id=msg.id, name="Test Place", bookmark_yn=False)
    db.add(place)
    db.commit()
    db.refresh(place)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 북마크 True 설정
        response = await client.patch(
            f"/api/chat/places/{place.id}/bookmark?bookmark=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["bookmark_yn"] is True

        # DB 확인
        db.refresh(place)
        assert place.bookmark_yn is True


@pytest.mark.asyncio
async def test_update_room_bookmark(user_and_room):
    """ChatRoom 북마크 PATCH API 동작 확인"""
    user, room, token, db = user_and_room

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/chat/rooms/{room.id}/bookmark?bookmark=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["bookmark_yn"] is True

        db.refresh(room)
        assert room.bookmark_yn is True


@pytest.mark.asyncio
async def test_update_room_bookmark_permission_denied(user_and_room):
    """다른 사용자 방 북마크 변경 시 404 처리"""
    user, room, token, db = user_and_room
    other = User(email="other@test.com", name="Other")
    db.add(other)
    db.commit()
    db.refresh(other)
    other_token = create_access_token(other.email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/chat/rooms/{room.id}/bookmark?bookmark=true",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_bookmarked_rooms_returns_latest_preview(user_and_room):
    """북마크된 방 목록과 최신 메시지 미리보기 반환 확인"""
    user, room, token, db = user_and_room
    room.bookmark_yn = True
    db.add(room)

    msg1 = ChatMessage(room_id=room.id, message="첫 메시지", role="human")
    msg2 = ChatMessage(room_id=room.id, message="최신 메시지", role="ai")
    room2 = ChatRoom(user_id=user.id, title="Not Bookmarked")
    db.add_all([msg1, msg2, room2])
    db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/bookmarks/rooms",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == room.id
        assert body[0]["latest_message_preview"] == "최신 메시지"


@pytest.mark.asyncio
async def test_get_bookmarked_rooms_null_title_falls_back(user_and_room):
    """북마크 방 title이 NULL이어도 기본 제목으로 반환되어야 한다."""
    user, room, token, db = user_and_room
    room.bookmark_yn = True
    room.title = None
    db.add(room)
    db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/bookmarks/rooms",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["title"] == "새 채팅"


@pytest.mark.asyncio
async def test_get_bookmarked_places_only_user_scope(user_and_room):
    """북마크 장소 목록이 사용자 소유 방으로 제한되는지 확인"""
    user, room, token, db = user_and_room

    user_msg = ChatMessage(room_id=room.id, message="user msg", role="ai")
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    user_place = ChatPlace(messages_id=user_msg.id, name="User Place", bookmark_yn=True)
    db.add(user_place)

    other = User(email="other2@test.com", name="Other2")
    db.add(other)
    db.commit()
    db.refresh(other)
    other_room = ChatRoom(user_id=other.id, title="Other Room")
    db.add(other_room)
    db.commit()
    db.refresh(other_room)
    other_msg = ChatMessage(room_id=other_room.id, message="other msg", role="ai")
    db.add(other_msg)
    db.commit()
    db.refresh(other_msg)
    other_place = ChatPlace(messages_id=other_msg.id, name="Other Place", bookmark_yn=True)
    db.add(other_place)
    db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/bookmarks/places",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "User Place"
        assert body[0]["room_id"] == room.id
        assert body[0]["room_title"] == room.title


@pytest.mark.asyncio
async def test_get_bookmarked_places_null_room_title_falls_back(user_and_room):
    """북마크 장소의 room_title이 NULL이어도 기본 제목으로 반환되어야 한다."""
    user, room, token, db = user_and_room
    room.title = None
    db.add(room)
    db.commit()

    msg = ChatMessage(room_id=room.id, message="msg", role="ai")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    place = ChatPlace(messages_id=msg.id, name="User Place", bookmark_yn=True)
    db.add(place)
    db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/bookmarks/places",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["room_title"] == "새 채팅"


@pytest.mark.asyncio
async def test_bookmarked_places_numeric_empty_values_are_zero(user_and_room):
    """bookmarks/places 숫자 결측값은 0으로 정규화되어야 한다."""
    user, room, token, db = user_and_room

    msg = ChatMessage(room_id=room.id, message="msg", role="ai")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    place = ChatPlace(
        messages_id=msg.id,
        place_id=None,
        name="No Numeric",
        longitude=None,
        latitude=None,
        bookmark_yn=True,
    )
    db.add(place)
    db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/bookmarks/places",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["place_id"] == 0
        assert body[0]["longitude"] == 0.0
        assert body[0]["latitude"] == 0.0


@pytest.mark.asyncio
async def test_message_bookmark_route_removed(user_and_room):
    """메시지 북마크 PATCH 라우트 제거 확인"""
    user, room, token, db = user_and_room
    msg = ChatMessage(room_id=room.id, message="test", role="ai")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/chat/messages/{msg.id}/bookmark?bookmark=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_autostart_stream_trip_context_success(user_and_room):
    """autostart/stream(trip_context) 정상 동작"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/autostart/stream",
                json={
                    "mode": "trip_context",
                    "trip_context": {
                        "travel_duration": "2026-03-10 ~ 2026-03-12",
                        "adult_count": 2,
                        "child_count": 1,
                    },
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            lines = response.text.strip().split("\n\n")
            last_data = json.loads(lines[-1][6:])
            assert last_data.get("done") is True


@pytest.mark.asyncio
async def test_autostart_stream_selected_places_place_id_zero_becomes_unknown(user_and_room):
    """selected_places에서 place_id=0이면 unknown 텍스트로 프롬프트 생성"""
    user, room, token, db = user_and_room
    captured = {"user_input": ""}

    async def _mock_astream_events_capture(inputs, *args, **kwargs):
        captured["user_input"] = inputs.get("user_input", "")
        async for event in _mock_astream_events(*args, **kwargs):
            yield event

    mock_app = AsyncMock()
    mock_app.astream_events = _mock_astream_events_capture
    mock_app.nodes = {"intent": None, "planner": None, "retriever": None, "executor": None, "executor_missing": None}

    with patch("app.api.chat.get_graph_app", return_value=mock_app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/autostart/stream",
                json={
                    "mode": "selected_places",
                    "selected_places": [
                        {"name": "테스트 장소", "adress": "서울", "place_id": 0}
                    ],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    assert "ID: unknown" in captured["user_input"]


@pytest.mark.asyncio
async def test_autostart_stream_validation_errors(user_and_room):
    """mode별 필수 payload 누락 시 400"""
    user, room, token, db = user_and_room
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response_trip = await client.post(
            f"/api/chat/rooms/{room.id}/autostart/stream",
            json={"mode": "trip_context"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response_trip.status_code == 400

        response_places = await client.post(
            f"/api/chat/rooms/{room.id}/autostart/stream",
            json={"mode": "selected_places", "selected_places": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response_places.status_code == 400


@pytest.mark.asyncio
async def test_autostart_stream_default_skip_user_message_save(user_and_room):
    """autostart 기본값(save_user_message=False)일 때 human 메시지 미저장"""
    user, room, token, db = user_and_room

    with patch("app.api.chat.get_graph_app", return_value=_get_mock_graph_app()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/chat/rooms/{room.id}/autostart/stream",
                json={
                    "mode": "trip_context",
                    "trip_context": {
                        "travel_duration": "2026-03-10 ~ 2026-03-12",
                        "adult_count": 1,
                        "child_count": 0,
                    },
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    human_messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.role == "human",
    ).all()
    ai_messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.role == "ai",
    ).all()
    assert len(human_messages) == 0
    assert len(ai_messages) == 1
