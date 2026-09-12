"""Entrypoint for the combined SimWorld + Agent service.

    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from simworld.api import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)