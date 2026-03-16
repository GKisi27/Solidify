from app.core.database import SessionLocal
from app.models.history import History
from fastapi import APIRouter

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/user/{user_id}")
def get_history_for_user(user_id: int):
    db = SessionLocal()
    try:
        history_entries = db.query(History).filter(History.user_id == user_id).order_by(History.id.desc()).all()
        return history_entries
    finally:
        db.close()
        
    