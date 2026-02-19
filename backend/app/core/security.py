from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
def create_jwt_secret_key():
    import secrets
    return secrets.token_hex(32)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", create_jwt_secret_key())
ALGORITHM = "HS256"

ACCESS_EXPIRE = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_EXPIRE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/google/callback") 

def create_access_token(user_id: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE)
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: str):
    expire = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get current user (Access Token Validation)
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        if payload.get("type") != "access":
             raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 이메일로 사용자 조회
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Helper to verify refresh token
def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
             return None
        return payload.get("sub") # email
    except JWTError:
        return None

from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req # Rename to avoid conflict

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "postmessage"

def verify_google_auth_code(code: str):
    # Exchange Auth Code for Tokens
    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    response = req.post(token_endpoint, data=data)
    if response.status_code != 200:
        print(f"Google Token Exchange Failed: {response.text}")
        return {"error": response.text}
        
    tokens = response.json()
    id_token_str = tokens.get("id_token")
    
    # Verify ID Token
    try:
        # Allow small clock skew because local/dev environments sometimes drift a few seconds
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=30
        )
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
             raise ValueError('Wrong issuer.')
             
        # Return all info including tokens
        return {
            "id_info": id_info,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"), # May be None if already authorized
            "expires_in": tokens.get("expires_in")
        }
    except ValueError as e:
        print(f"Invalid Google ID Token: {e}")
        return {"error": str(e)}
