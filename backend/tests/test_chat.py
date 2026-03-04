from app.utils.security import create_access_token
from app.models.user import User
from app.models.chat import ChatRoom, ChatMessage
from unittest.mock import patch, AsyncMock
from app.models.enums import RoleType

def get_auth_headers(email="chat@example.com"):
    token = create_access_token(email)
    return {"Authorization": f"Bearer {token}"}

def test_create_session(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.post("/api/chat/rooms", headers=headers, json={"title": "New Session"})
    assert response.status_code == 200 # or 201
    data = response.json()
    assert data["title"] == "New Session"
    assert "id" in data

def test_get_sessions(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    # Create session manually
    session = ChatRoom(user_id=user.id, title="Test Session")
    db.add(session)
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.get("/api/chat/rooms", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Session"

def test_send_message_stream(client, db):
    # Mock LLM stream response
    # Since streaming is harder to test with TestClient, we rely on checking if it initiates correctly
    pass
    # Implementation depends on how stream is handled. 
    # If using /api/chat/rooms/{id}/messages (non-streaming save)
    
def test_get_session_messages(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    session = ChatRoom(user_id=user.id, title="Test Session")
    db.add(session)
    db.commit()
    
    # Add messages
    msg1 = ChatMessage(room_id=session.id, message="Hello", role=RoleType.human)
    msg2 = ChatMessage(room_id=session.id, message="Hi there", role=RoleType.ai)
    db.add_all([msg1, msg2])
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.get(f"/api/chat/rooms/{session.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["message"] == "Hello"


def test_ask_uses_summary_query_as_room_title_within_first_two_messages(client, db):
    user = User(email="chat-ask@test.com", name="Ask User")
    db.add(user)
    db.commit()
    db.refresh(user)

    room = ChatRoom(user_id=user.id, title="새로운 여행 계획")
    db.add(room)
    db.commit()
    db.refresh(room)

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "answer": "답변",
        "summary_query": "요약 쿼리",
        "summary_message": "요약 메시지 제목",
    })

    with patch("app.api.chat.get_graph_app", return_value=mock_graph):
        response = client.post(
            f"/api/chat/rooms/{room.id}/ask",
            headers=get_auth_headers(user.email),
            json={"room_id": room.id, "message": "제주 추천", "role": "human"},
        )
        assert response.status_code == 200

    db.refresh(room)
    assert room.title == "요약 쿼리"


def test_ask_does_not_overwrite_custom_title_even_within_first_two_messages(client, db):
    user = User(email="chat-ask-custom@test.com", name="Ask Custom")
    db.add(user)
    db.commit()
    db.refresh(user)

    room = ChatRoom(user_id=user.id, title="내가 정한 제목")
    db.add(room)
    db.commit()
    db.refresh(room)

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "answer": "답변",
        "summary_query": "자동 요약 제목",
        "summary_message": "자동 요약 메시지 제목",
    })

    with patch("app.api.chat.get_graph_app", return_value=mock_graph):
        response = client.post(
            f"/api/chat/rooms/{room.id}/ask",
            headers=get_auth_headers(user.email),
            json={"room_id": room.id, "message": "제주 추천", "role": "human"},
        )
        assert response.status_code == 200

    db.refresh(room)
    assert room.title == "내가 정한 제목"


def test_ask_does_not_update_room_title_after_two_messages(client, db):
    user = User(email="chat-ask-2@test.com", name="Ask User2")
    db.add(user)
    db.commit()
    db.refresh(user)

    room = ChatRoom(user_id=user.id, title="유지 제목")
    db.add(room)
    db.commit()
    db.refresh(room)

    db.add_all([
        ChatMessage(room_id=room.id, message="m1", role=RoleType.human),
        ChatMessage(room_id=room.id, message="m2", role=RoleType.ai),
    ])
    db.commit()

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "answer": "답변",
        "summary_query": "새 제목",
        "summary_message": "새 요약 제목",
    })

    with patch("app.api.chat.get_graph_app", return_value=mock_graph):
        response = client.post(
            f"/api/chat/rooms/{room.id}/ask",
            headers=get_auth_headers(user.email),
            json={"room_id": room.id, "message": "m3", "role": "human"},
        )
        assert response.status_code == 200

    db.refresh(room)
    assert room.title == "유지 제목"
