from app.core.database import SessionLocal
from app.models.history import History
from app.dependencies.auth import get_current_user
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/user/{user_id}")
def get_history_for_user(user_id: int, current_user: User = Depends(get_current_user)):
    # Users can only fetch their own history
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this history")
    
    db = SessionLocal()
    try:
        history_entries = (
            db.query(History)
            .filter(History.user_id == user_id)
            .order_by(History.id.desc())
            .all()
        )
        return history_entries
    finally:
        db.close()


@router.get("/{history_id}")
def get_history_item(history_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        item = (
            db.query(History)
            .filter(History.id == history_id, History.user_id == current_user.id)
            .first()
        )
    finally:
        db.close()

    if not item:
        raise HTTPException(status_code=404, detail="History item not found")

    return {
        "status": "done",
        "file_name": item.filename,
        "converted_image": f"data:image/png;base64,{item.image_base64}",
        "doc_url": item.doc_url,
        "gemini_json": item.gemini_data,
        "converted_json": item.converted_data,
    }