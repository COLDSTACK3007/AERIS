import sys
import os
import traceback

backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_path))

from fastapi import FastAPI

app = FastAPI(title="AERIS Serverless Gateway")

@app.get("/api/ping")
@app.get("/ping")
def ping_endpoint():
    return {"status": "ok", "message": "AERIS Vercel Python serverless gateway is active!"}

try:
    from app.main import app as main_app
    # Mount main_app under both /api and / for complete routing coverage
    app.mount("/api", main_app)
    app.mount("/", main_app)
except Exception as e:
    err_str = str(e)
    tb_str = traceback.format_exc()

    @app.get("/api/debug-error")
    @app.get("/debug-error")
    def debug_error():
        return {"status": "init_error", "error": err_str, "traceback": tb_str}
