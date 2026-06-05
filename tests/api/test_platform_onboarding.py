from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402
from nimbusware_maker.onboarding import onboarding_flag_path  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_onboarding_round_trip(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    flag = tmp_path / "onboarded"
    monkeypatch.setenv("NIMBUSWARE_MAKER_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "nimbusware_maker.onboarding.onboarding_flag_path",
        lambda: flag,
    )
    r = client.get("/v1/platform/onboarding")
    assert r.status_code == 200
    assert r.json()["onboarded"] is False
    r2 = client.post("/v1/platform/onboarding")
    assert r2.status_code == 200
    assert r2.json()["onboarded"] is True
    r3 = client.get("/v1/platform/onboarding")
    assert r3.json()["onboarded"] is True
    _ = onboarding_flag_path
