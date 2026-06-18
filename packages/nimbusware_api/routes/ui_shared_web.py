from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

UI_SHARED_DIR = Path(__file__).resolve().parents[2] / "nimbusware_ui_shared"


def mount_ui_shared(app: FastAPI) -> None:
    """Serve shared Maker/Admin UI modules at ``/v1/nimbusware_ui_shared``."""
    if not UI_SHARED_DIR.is_dir():
        return
    app.mount(
        "/v1/nimbusware_ui_shared",
        StaticFiles(directory=str(UI_SHARED_DIR), html=False),
        name="ui_shared",
    )
