import hashlib
from models.user import User
from core.database import SessionLocal
import secrets  

def login_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()

        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        if not user or user.password != hashed_input:
            return None

        token = secrets.token_hex(16)

        return {
            "token": token,
            "user_id": user.id,
            "username": user.username
        }

    finally:
        db.close()
