# app/services/auth_services.py
import hashlib
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User

SECRET_KEY = "Solidify" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Login function returns a JWT token
def login_user(username: str, password: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        if not user or user.password != hashed_input:
            return None

        # Create JWT payload
        expire =  datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {"user_id": user.id, "exp": expire}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "token": token,
            "user_id": user.id,
            "username": user.username
        }
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        db: Session = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        db.close()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")