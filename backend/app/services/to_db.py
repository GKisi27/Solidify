import base64
from app.core.database import SessionLocal, engine
from app.models.history import History, HistoryType
from app.models.user import User

def save_history(
    image_bytes: bytes,
    user_id: int,           # ← add this
    filename: str = "example.png",
    history_type: HistoryType = HistoryType.convert_to_3d,
    gemini_json: dict | None = None,
    converted_json: dict | None = None,
    doc_url: str | None = None
):
    image_base64_str = base64.b64encode(image_bytes).decode("utf-8")
    db = SessionLocal()
    
    print(user_id)  # Debug: Check the user_id being passed

    try:
        history_entry = History(
            user_id=user_id,   # ← use directly, no User query needed
            type=history_type,
            filename=filename,
            image_base64=image_base64_str,
            doc_url=doc_url,
            gemini_data=gemini_json,
            converted_data=converted_json,
        )

        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)
        return history_entry

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()