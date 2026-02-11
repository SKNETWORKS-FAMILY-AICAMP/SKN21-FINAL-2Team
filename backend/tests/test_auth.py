from unittest.mock import patch

def test_login_google_success(client):
    # Mock verify_google_auth_code to return success
    mock_auth_result = {
        "id_info": {
            "email": "test@example.com",
            "name": "Test User",
            "sub": "123456789",
            "iss": "accounts.google.com"
        },
        "access_token": "mock_google_access_token",
        "refresh_token": "mock_google_refresh_token"
    }
    
    with patch("app.api.auth.verify_google_auth_code", return_value=mock_auth_result):
        response = client.post("/api/auth/google", json={"code": "valid_auth_code"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

def test_login_google_failure(client):
    # Mock failure
    with patch("app.api.auth.verify_google_auth_code", return_value=None):
        response = client.post("/api/auth/google", json={"code": "invalid_code"})
        assert response.status_code == 400

def test_refresh_token(client, db):
    # 1. Create a user manually
    from app.models.user import User
    user = User(email="test@example.com", name="Test")
    db.add(user)
    db.commit()
    
    # 2. Get a valid refresh token directly from helper (or login first)
    from app.core.security import create_refresh_token
    token = create_refresh_token(data={"sub": "test@example.com"})
    
    # 3. Call refresh endpoint
    response = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
