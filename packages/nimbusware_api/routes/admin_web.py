from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ADMIN_STATIC_DIR = Path(__file__).resolve().parents[2] / "nimbusware_admin_ui" / "dist"


def mount_admin_web(app: FastAPI) -> None:
    """Serve the Admin Preact SPA at ``/v1/admin/app`` when ``dist/`` exists."""
    if not ADMIN_STATIC_DIR.is_dir():
        return
    app.mount(
        "/v1/admin/app",
        StaticFiles(directory=str(ADMIN_STATIC_DIR), html=True),
        name="admin_web",
    )
