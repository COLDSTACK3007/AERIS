import os
import shutil
from pydantic_settings import BaseSettings
from typing import List

default_db_url = "sqlite:///./aeris.db"
if os.environ.get("VERCEL") or not os.access(".", os.W_OK):
    tmp_db = "/tmp/aeris.db"
    existing_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "aeris.db"))
    if os.path.exists(existing_db) and not os.path.exists(tmp_db):
        try:
            shutil.copy2(existing_db, tmp_db)
        except Exception:
            pass
    default_db_url = f"sqlite:///{tmp_db}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AERIS — Launch Vehicle Telemetry Framework"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = default_db_url
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
