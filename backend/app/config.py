from pydantic_settings import BaseSettings
from typing import List
import os

def _default_db_url() -> str:
    """Use /tmp on Vercel (read-only filesystem), local path otherwise."""
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/aeris.db"
    return "sqlite:///./aeris.db"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AERIS — Launch Vehicle Telemetry Framework"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = _default_db_url()
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
