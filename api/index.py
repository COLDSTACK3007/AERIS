import sys
import os
import traceback

# Ensure backend package is importable
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_path))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Gateway app that Vercel's serverless runtime will invoke
app = FastAPI(title="AERIS Serverless Gateway")

@app.get("/api/ping")
def ping_endpoint():
    return {"status": "ok", "message": "AERIS Vercel serverless gateway is active!"}

# Try to import the real FastAPI app from the backend.
# On Vercel, requests arrive as /api/telemetry/upload etc.
# The rewrite in vercel.json sends /api/(.*) -> /api (this file).
# Vercel sets the actual requested path in the request, so the
# ASGI app sees the ORIGINAL path, e.g. /api/telemetry/upload.
#
# The backend main_app already registers routes under /api prefix
# (settings.API_V1_STR = "/api"), so we must NOT mount it under
# /api again — just use it directly as the handler.
try:
    from app.main import app as main_app
    # Use main_app directly — it already has /api-prefixed routes.
    # We replace our gateway app with it entirely so route resolution works.
    app = main_app
except Exception as e:
    err_str = str(e)
    tb_str = traceback.format_exc()
    print(f"[AERIS] Failed to import backend app: {err_str}")
    print(tb_str)

    @app.get("/api/debug-error")
    def debug_error():
        return {"status": "init_error", "error": err_str, "traceback": tb_str}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def catch_all_error(path: str):
        return JSONResponse(
            status_code=503,
            content={
                "detail": f"Backend failed to initialize: {err_str}",
                "hint": "Visit /api/debug-error for full traceback"
            }
        )
