import sys
import os
import traceback

backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_path))

try:
    from app.main import app
except Exception as e:
    err_str = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def catch_all(full_path: str = ""):
        return JSONResponse(status_code=200, content={"status": "init_error", "error": str(e), "traceback": err_str})
