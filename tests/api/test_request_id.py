from __future__ import annotations

from fastapi.testclient import TestClient

from nimbusware_api.app import app


def test_response_includes_generated_request_id() -> None:
    client = TestClient(app)
    resp = client.get("/v1/platform/edition")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-Id")
    assert rid
    assert len(rid) >= 8


def test_request_id_echoes_client_header() -> None:
    client = TestClient(app)
    resp = client.get("/v1/platform/edition", headers={"X-Request-Id": "client-req-123"})
    assert resp.headers.get("X-Request-Id") == "client-req-123"


def test_request_id_on_not_found() -> None:
    client = TestClient(app)
    resp = client.get("/v1/runs/not-a-uuid", headers={"X-Request-Id": "not-found-req"})
    assert resp.status_code in (404, 422)
    assert resp.headers.get("X-Request-Id") == "not-found-req"


def test_request_id_generated_when_header_blank() -> None:
    client = TestClient(app)
    resp = client.get("/v1/platform/edition", headers={"X-Request-Id": "   "})
    rid = resp.headers.get("X-Request-Id")
    assert rid and rid.strip()
