from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db   # make sure get_db is exported from here
from app.models.history import History
from app.dependencies.auth import get_current_user
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/user/{user_id}")
def get_history_for_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    print(current_user.id)
    print(f"user_id param: {user_id}")
    
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this history")

    history_entries = (
        db.query(History)
        .filter(History.user_id == user_id)
        .order_by(History.id.desc())
        .all()
    )
    return history_entries


@router.get("/{history_id}")
def get_history_item(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(History)
        .filter(History.id == history_id, History.user_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="History item not found")

    # Access attributes while session is still open (managed by get_db dependency)
    return {
        "status": "done",
        "file_name": item.filename,
        "converted_image": f"data:image/png;base64,{item.image_base64}",
        "doc_url": item.doc_url,
        "gemini_json": item.gemini_data,
        "converted_json": item.converted_data,
    }
