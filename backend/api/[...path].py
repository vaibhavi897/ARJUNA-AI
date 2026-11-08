"""Vercel entry point: every /api/... request is served by the FastAPI app.

The file name is a catch-all route, so Vercel passes the original request path to the app (a rewrite to a single
file would hand the app the file's own path instead, and every route would return 404).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401
