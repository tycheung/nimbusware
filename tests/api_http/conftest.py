from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", DEFAULT_NIMBUSWARE_ADMIN_TOKEN)

from api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
