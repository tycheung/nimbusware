from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from api.app import (  # noqa: E402
    app,
    nimbusware_http_exception_handler,
    nimbusware_validation_handler,
)
from api.errors import problem  # noqa: E402


def test_problem_without_type_preserves_v1_flat_shape() -> None:
    body = problem("not_found", "resource missing")
    assert body == {"code": "not_found", "message": "resource missing"}
    assert "type" not in body


def test_problem_with_type_includes_uri() -> None:
    uri = "https://nimbusware.dev/problems/not-found"
    body = problem("not_found", "resource missing", type=uri)
    assert body["type"] == uri
    assert body["code"] == "not_found"
    assert body["message"] == "resource missing"


def test_problem_with_type_and_details() -> None:
    uri = "https://nimbusware.dev/problems/validation-error"
    body = problem(
        "validation_error",
        "bad input",
        type=uri,
        details={"field": "workflow_profile"},
    )
    assert body == {
        "type": uri,
        "code": "validation_error",
        "message": "bad input",
        "details": {"field": "workflow_profile"},
    }


def test_http_exception_handler_emits_problem_json_without_type() -> None:
    detail = problem("run_not_found", "run not found", details={"run_id": "abc"})
    exc = HTTPException(status_code=404, detail=detail)
    scope = {"type": "http", "method": "GET", "path": "/v1/runs/x", "headers": []}
    request = Request(scope)
    response = asyncio.run(nimbusware_http_exception_handler(request, exc))
    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    data = json.loads(response.body.decode())
    assert data["code"] == "run_not_found"
    assert "type" not in data


def test_http_exception_handler_emits_problem_json_with_type() -> None:
    uri = "https://nimbusware.dev/problems/run-not-found"
    detail = problem("run_not_found", "run not found", type=uri)
    exc = HTTPException(status_code=404, detail=detail)
    scope = {"type": "http", "method": "GET", "path": "/v1/runs/x", "headers": []}
    request = Request(scope)
    response = asyncio.run(nimbusware_http_exception_handler(request, exc))
    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    assert uri in response.body.decode()


def test_validation_handler_emits_problem_json_without_type() -> None:
    scope = {"type": "http", "method": "POST", "path": "/v1/runs", "headers": []}
    request = Request(scope)
    exc = RequestValidationError(
        errors=[{"loc": ("body",), "msg": "field required", "type": "missing"}]
    )
    response = asyncio.run(nimbusware_validation_handler(request, exc))
    assert response.status_code == 422
    assert response.media_type == "application/problem+json"
    data = json.loads(response.body.decode())
    assert data["code"] == "validation_error"
    assert "type" not in data


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_route_validation_still_returns_problem_json(client: TestClient) -> None:
    response = client.post("/v1/runs/not-a-uuid/actions/retry")
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    data = response.json()
    assert data["code"] == "validation_error"
    assert "type" not in data
