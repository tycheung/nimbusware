from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response
from starlette.types import Scope

ADMIN_STATIC_DIR = Path(__file__).resolve().parents[2] / "nimbusware_admin_ui" / "dist"
_ADMIN_INDEX = ADMIN_STATIC_DIR / "index.html"


class AdminSPAStaticFiles(StaticFiles):
    """Serve built assets; fall back to index.html for client-side routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or not _ADMIN_INDEX.is_file():
                raise
            return FileResponse(_ADMIN_INDEX)


def mount_admin_web(app: FastAPI) -> None:
    """Serve the Admin Preact SPA at ``/v1/admin/app`` when ``dist/`` exists."""
    if not ADMIN_STATIC_DIR.is_dir():
        return
    app.mount(
        "/v1/admin/app",
        AdminSPAStaticFiles(directory=str(ADMIN_STATIC_DIR), html=True),
        name="admin_web",
    )
