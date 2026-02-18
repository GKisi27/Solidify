from  app.models.user import User
from app.core.database import SessionLocal

def login_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user and user.password != password:
            return {"message": "Invalid username or password"}
    
        return {"message": "Login Successful", "user_id": user.id}

    finally:
        db.close()