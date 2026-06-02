"""Product entry modules import without network I/O."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)


def test_nimbusware_api_app_importable() -> None:
    from nimbusware_api.app import app

    assert app.title
    assert any(route.path.startswith("/v1") for route in app.routes)


def test_nimbusware_maker_app_importable() -> None:
    import nimbusware_maker.app  # noqa: F401
    from nimbusware_maker.ui import render_main

    assert callable(render_main)
