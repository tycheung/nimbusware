from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app, custom_openapi


def test_custom_openapi_is_cached() -> None:
    app.openapi_schema = None
    first = custom_openapi()
    second = custom_openapi()
    assert first is second
    assert "openapi" in first


def test_lifespan_starts_without_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    with TestClient(app) as client:
        resp = client.get("/v1/platform/edition")
        assert resp.status_code == 200
