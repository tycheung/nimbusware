from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from maker_web import STATIC_DIR


def mount_maker_web(app: FastAPI) -> None:
    """Serve the Maker web UI at ``/v1/maker/app`` (mount on app, not sub-router)."""
    app.mount(
        "/v1/maker/app",
        StaticFiles(directory=str(STATIC_DIR), html=True),
        name="maker_web",
    )
