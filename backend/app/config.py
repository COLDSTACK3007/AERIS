import os
import shutil
from pydantic_settings import BaseSettings
from typing import List

default_db_url = "sqlite:///./aeris.db"
if os.environ.get("VERCEL") or not os.access(".", os.W_OK):
    tmp_db = "/tmp/aeris.db"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(base_dir, "..", "aeris.db")),
        os.path.abspath(os.path.join(base_dir, "..", "..", "backend", "aeris.db")),
        os.path.abspath(os.path.join(base_dir, "..", "..", "aeris.db")),
        os.path.abspath("backend/aeris.db"),
        os.path.abspath("aeris.db"),
    ]
    for cand in candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 1000:
            if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) < 1000:
                try:
                    shutil.copy2(cand, tmp_db)
                except Exception as e:
                    print(f"Failed to copy DB from {cand}: {e}")
            break
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
