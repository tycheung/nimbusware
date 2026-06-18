from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from e2e.harness.env import DEFAULT_E2E_ENV, apply_e2e_unit_profile
from nimbusware_env import find_repo_root

_REPO = find_repo_root(start=Path(__file__).resolve())
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))
for _key, _value in DEFAULT_E2E_ENV.items():
    os.environ.setdefault(_key, _value)

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def journey_client(monkeypatch: pytest.MonkeyPatch):
    from e2e.harness.journey import JourneyClient

    apply_e2e_unit_profile(monkeypatch, repo_root=str(_REPO))
    with TestClient(app) as client:
        yield JourneyClient(client=client)
