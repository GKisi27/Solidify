import base64
from app.core.database import SessionLocal
from app.models.history import History
from app.models.user import User


def save_image(image_bytes):
    image_base64_str = base64.b64encode(image_bytes).decode("utf-8")

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            raise Exception("No users found in the database!")

        history_entry = History(
            user_id=user.id,
            filename="example.png",
            image_base64=image_base64_str,
        )

        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        print(f"Inserted history record for user {user.username} with id {history_entry.id}")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
        
def save_json(gemini_json, converted_json):
    db = SessionLocal()
    try:
        history_entry = db.query(History).order_by(History.id.desc()).first()

        if not history_entry:
            raise Exception("No history record found!")

        history_entry.gemini_data = gemini_json
        history_entry.converted_data = converted_json

        db.commit()
        db.refresh(history_entry)

        print(f"Updated history record {history_entry.id}")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
import base64
from app.core.database import SessionLocal
from app.models.history import History
from app.models.user import User


def save_image(image_bytes):
    image_base64_str = base64.b64encode(image_bytes).decode("utf-8")

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            raise Exception("No users found in the database!")

        history_entry = History(
            user_id=user.id,
            filename="example.png",
            image_base64=image_base64_str,
        )

        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        print(f"Inserted history record for user {user.username} with id {history_entry.id}")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
        
def save_json(gemini_json, converted_json):
    db = SessionLocal()
    try:
        history_entry = db.query(History).order_by(History.id.desc()).first()

        if not history_entry:
            raise Exception("No history record found!")

        history_entry.gemini_data = gemini_json
        history_entry.converted_data = converted_json

        db.commit()
        db.refresh(history_entry)

        print(f"Updated history record {history_entry.id}")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()