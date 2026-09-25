from pydantic_settings import BaseSettings
from typing import List
import os

def _default_db_url() -> str:
    """Use /tmp on Vercel or read-only filesystem environments, local path otherwise."""
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("NOW_REGION"):
        return "sqlite:////tmp/aeris.db"
    try:
        test_file = "./.write_test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return "sqlite:///./aeris.db"
    except Exception:
        return "sqlite:////tmp/aeris.db"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AERIS — Launch Vehicle Telemetry Framework"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = _default_db_url()
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
