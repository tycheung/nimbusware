from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from e2e.harness.env import apply_e2e_unit_profile
from nimbusware_env import find_repo_root
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

_REPO = find_repo_root(start=Path(__file__).resolve())
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", DEFAULT_NIMBUSWARE_ADMIN_TOKEN)

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def journey_client(monkeypatch: pytest.MonkeyPatch):
    from e2e.harness.journey import JourneyClient

    apply_e2e_unit_profile(monkeypatch, repo_root=str(_REPO))
    with TestClient(app) as client:
        yield JourneyClient(client=client)
