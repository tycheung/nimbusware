"""Product entry modules import without network I/O."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)


def test_nimbusware_api_app_importable() -> None:
    from nimbusware_api.app import app

    assert app.title
    assert any(route.path.startswith("/v1") for route in app.routes)


def test_nimbusware_maker_web_importable() -> None:
    from nimbusware_maker_web import STATIC_DIR

    assert (STATIC_DIR / "index.html").is_file()
