from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from nimbusware_api.app import (  # noqa: E402
    app,
    nimbusware_uncaught_exception_handler,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_422, PROBLEM_RESPONSE_500
from nimbusware_api.schemas.problem import Problem


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_problem_response_500_matches_problem_schema() -> None:
    schema = Problem.model_json_schema()
    content = PROBLEM_RESPONSE_500["content"]
    assert content["application/json"]["schema"] == schema
    assert content["application/problem+json"]["schema"] == schema
    assert "internal" in PROBLEM_RESPONSE_500["description"].lower() or "500" in str(
        PROBLEM_RESPONSE_500["description"],
    )


def test_problem_response_422_matches_problem_schema() -> None:
    schema = Problem.model_json_schema()
    content = PROBLEM_RESPONSE_422["content"]
    assert content["application/json"]["schema"] == schema
    assert content["application/problem+json"]["schema"] == schema


def test_uncaught_exception_handler_returns_problem_json() -> None:
    scope = {"type": "http", "method": "GET", "path": "/boom", "headers": []}
    request = Request(scope)
    response = asyncio.run(
        nimbusware_uncaught_exception_handler(request, RuntimeError("deliberate")),
    )
    assert response.status_code == 500
    assert response.media_type == "application/problem+json"
    body = response.body.decode()
    assert "internal_error" in body
    assert "deliberate" not in body


def test_openapi_app_documents_default_500(client: TestClient) -> None:
    spec = client.app.openapi()
    post_runs = spec["paths"]["/v1/runs"]["post"]["responses"]
    assert "500" in post_runs
    assert "application/problem+json" in post_runs["500"]["content"]


def test_create_run_openapi_post_documents_500(client: TestClient) -> None:
    spec = client.app.openapi()
    responses = spec["paths"]["/v1/runs"]["post"]["responses"]
    assert "500" in responses
    assert "422" in responses


def test_lifecycle_mutating_routes_document_500(client: TestClient) -> None:
    spec = client.app.openapi()
    paths = spec["paths"]
    for suffix in ("lifecycle/start", "lifecycle/plan", "lifecycle/verify"):
        key = f"/v1/runs/{{run_id}}/{suffix}"
        post = paths[key]["post"]["responses"]
        assert "500" in post, key


def test_get_runs_list_documents_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    responses = spec["paths"]["/v1/runs"]["get"]["responses"]
    assert "500" in responses
    assert "application/problem+json" in responses["500"]["content"]


def test_get_run_detail_documents_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    responses = spec["paths"]["/v1/runs/{run_id}"]["get"]["responses"]
    assert "500" in responses
    assert "application/problem+json" in responses["500"]["content"]


def test_get_run_timeline_documents_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    path = "/v1/runs/{run_id}/timeline"
    responses = spec["paths"][path]["get"]["responses"]
    assert "500" in responses
    assert "application/problem+json" in responses["500"]["content"]


def test_get_run_findings_documents_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    path = "/v1/runs/{run_id}/findings"
    responses = spec["paths"][path]["get"]["responses"]
    assert "500" in responses
    assert "application/problem+json" in responses["500"]["content"]


def test_runs_read_paths_document_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    for path in (
        "/v1/runs",
        "/v1/runs/{run_id}",
        "/v1/runs/{run_id}/timeline",
        "/v1/runs/{run_id}/findings",
    ):
        responses = spec["paths"][path]["get"]["responses"]
        assert "500" in responses, path
        assert "application/problem+json" in responses["500"]["content"], path


def test_read_and_action_routes_document_500_problem_json(client: TestClient) -> None:
    spec = client.app.openapi()
    checks: list[tuple[str, str]] = [
        ("/v1/bundles/search", "get"),
        ("/v1/personas", "get"),
        ("/v1/runs/{run_id}/actions/retry", "post"),
        ("/v1/runs/{run_id}/actions/escalate", "post"),
        ("/v1/runs/{run_id}/actions/override-gate", "post"),
        ("/v1/roles/{role_id}/execute", "post"),
    ]
    for path, method in checks:
        responses = spec["paths"][path][method]["responses"]
        assert "500" in responses, f"{method.upper()} {path}"
        assert "application/problem+json" in responses["500"]["content"], f"{method.upper()} {path}"


def test_preflight_history_openapi_keeps_success_fields_and_metrics_export(
    client: TestClient,
) -> None:
    spec = client.app.openapi()
    schema = spec["paths"]["/v1/preflight-history"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    props = schema["properties"]
    # Keep existing success payload fields stable.
    assert "entries" in props
    assert "runs_with_preflight" in props
    assert "distinct_validated_model_id_count" in props
    # New explicit export contract remains documented.
    assert "metrics_export" in props
    assert props["metrics_export"]["type"] == ["object", "null"]
