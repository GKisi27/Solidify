from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()

try:
    user = User(
        username="admin",
        password=hash_password("admin123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"✅ User created: {user.username} (id={user.id})")
except Exception as e:
    db.rollback()
    print(f"❌ Failed: {e}")
finally:
    db.close()