from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()