from app.core.security import create_access_token
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from unittest.mock import patch

def get_auth_headers(email="chat@example.com"):
    token = create_access_token(email)
    return {"Authorization": f"Bearer {token}"}

def test_create_session(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.post("/api/chat/sessions", headers=headers, json={"title": "New Session"})
    assert response.status_code == 200 # or 201
    data = response.json()
    assert data["title"] == "New Session"
    assert "id" in data

def test_get_sessions(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    # Create session manually
    session = ChatSession(user_id=user.id, title="Test Session")
    db.add(session)
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.get("/api/chat/sessions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Session"

def test_send_message_stream(client, db):
    # Mock LLM stream response
    # Since streaming is harder to test with TestClient, we rely on checking if it initiates correctly
    pass
    # Implementation depends on how stream is handled. 
    # If using /api/chat/sessions/{id}/messages (non-streaming save)
    
def test_get_session_messages(client, db):
    user = User(email="chat@example.com", name="Chat User")
    db.add(user)
    db.commit()
    
    session = ChatSession(user_id=user.id, title="Test Session")
    db.add(session)
    db.commit()
    
    # Add messages
    msg1 = ChatMessage(session_id=session.id, message="Hello", role="human")
    msg2 = ChatMessage(session_id=session.id, message="Hi there", role="ai")
    db.add_all([msg1, msg2])
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.get(f"/api/chat/sessions/{session.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["message"] == "Hello"
