from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → go to project root
BASE_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str
    GEMINI_PAID_KEY: str

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=str(BASE_DIR / ".env.local"),
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()