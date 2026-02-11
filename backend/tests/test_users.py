from app.core.security import create_access_token
from app.models.user import User

def get_auth_headers(email="test@example.com"):
    token = create_access_token(email)
    return {"Authorization": f"Bearer {token}"}

def test_read_users_me(client, db):
    # Create User
    user = User(email="test@example.com", name="Test User", social_provider="google")
    db.add(user)
    db.commit()
    
    headers = get_auth_headers(user.email)
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"

def test_update_user_me(client, db):
    # Create User
    user = User(email="update@example.com", name="Old Name")
    db.add(user)
    db.commit()
    
    headers = get_auth_headers(user.email)
    payload = {"name": "New Name", "gender": "male"}
    
    response = client.patch("/api/users/me", headers=headers, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["gender"] == "male"
