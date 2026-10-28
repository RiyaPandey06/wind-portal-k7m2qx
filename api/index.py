"""Vercel serverless entry point: exposes the FastAPI app (ASGI) as the /api function."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402,F401  (Vercel looks for a module-level `app`)
