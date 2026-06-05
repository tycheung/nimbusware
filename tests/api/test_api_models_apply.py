from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ["NIMBUSWARE_HW_FIXTURE"] = "medium"

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_apply_preset_round_trip(client: TestClient, tmp_path) -> None:
    ranked = client.get("/v1/platform/models/ranked", params={"limit": 1})
    assert ranked.status_code == 200
    models = ranked.json().get("models") or []
    if not models:
        pytest.skip("no models in allowlist")
    model_id = models[0]["model_id"]
    r = client.post(
        "/v1/platform/models/apply-preset",
        json={"model_id": model_id, "preset": "balanced", "target": "model-routing"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "applied"
    assert body.get("preset_applied") == {
        "model_id": model_id,
        "preset": "balanced",
        "target": "model-routing",
    }


def test_apply_preset_invalid_preset(client: TestClient) -> None:
    r = client.post(
        "/v1/platform/models/apply-preset",
        json={"model_id": "llama3.2", "preset": "recommended"},
    )
    assert r.status_code == 422


def test_apply_preset_missing_model_id(client: TestClient) -> None:
    r = client.post(
        "/v1/platform/models/apply-preset",
        json={"preset": "balanced"},
    )
    assert r.status_code == 422
