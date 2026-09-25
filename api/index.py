import sys
import os

# Add backend directory to sys.path so 'from app.xxx' imports resolve
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_path))

from app.main import app
