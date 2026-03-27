import base64
from app.core.database import SessionLocal, engine
from app.models.history import History, HistoryType
from app.models.user import User


def save_history(
    image_bytes: bytes,
    filename: str = "example.png",
    history_type: HistoryType = HistoryType.convert_to_3d,
    gemini_json: dict | None = None,
    converted_json: dict | None = None,
    doc_url: str | None = None
):
    """
    Save an image to history and optionally update with JSON data.

    Args:
        image_bytes: Raw bytes of the image to store.
        filename: Name of the image file.
        history_type: Type of history record.
        gemini_json: Optional Gemini JSON data to attach.
        converted_json: Optional converted JSON data to attach.
    """
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")

    image_base64_str = base64.b64encode(image_bytes).decode("utf-8")
    db = SessionLocal()

    try:
        # Get the first user (or you could pass user_id explicitly)
        user = db.query(User).first()
        if not user:
            raise Exception("No users found in the database!")

        # Create a new history record
        history_entry = History(
            user_id=user.id,
            type=history_type,
            filename=filename,
            image_base64=image_base64_str,
            doc_url = doc_url,
            gemini_data=gemini_json,
            converted_data=converted_json,
        )

        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        print(f"Saved history record {history_entry.id} for user {user.username}")

        return history_entry

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()