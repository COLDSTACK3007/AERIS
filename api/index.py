import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.app.main import app

# ASGI middleware to ensure both /api/... and /... routes match correctly on Vercel
class VercelPathFixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            # If Vercel stripped /api, add it back so FastAPI /api routers match
            if not path.startswith("/api"):
                new_path = "/api" + path if path.startswith("/") else "/api/" + path
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode("utf-8")
        await self.app(scope, receive, send)

handler = VercelPathFixMiddleware(app)
