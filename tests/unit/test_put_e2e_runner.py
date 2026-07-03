from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestrator.put_e2e_runner import (
    list_factory_flow_ids,
    load_factory_flow,
    match_factory_flow_id,
    run_put_e2e_flow,
    stub_console_capture,
    stub_network_capture,
)

REPO = Path(__file__).resolve().parents[2]


def _mock_response(
    *, status: int = 200, json_body: dict | None = None, text: str = "ok"
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = json.JSONDecodeError("no json", "", 0)
    return resp


def test_factory_flow_catalog_lists_templates() -> None:
    ids = list_factory_flow_ids(REPO)
    assert "crm" in ids
    assert "todo_api" in ids
    assert "contacts_api" in ids


def test_load_factory_flow_crm_has_steps() -> None:
    flow = load_factory_flow("crm", repo_root=REPO)
    assert flow["id"] == "crm"
    assert isinstance(flow.get("steps"), list)
    assert len(flow["steps"]) >= 2


def test_match_factory_flow_id_from_prompt_id() -> None:
    assert match_factory_flow_id("", prompt_id="todo_api", repo_root=REPO) == "todo_api"


def test_match_factory_flow_id_from_stack_manifest() -> None:
    manifest = {"surfaces": ["web"], "stacks": {"web": "react_vite"}}
    assert match_factory_flow_id("", stack_manifest=manifest, repo_root=REPO) == "static_site"


def test_stub_captures_return_findings() -> None:
    console = stub_console_capture(enabled=True)
    network = stub_network_capture(enabled=True, exercised_paths={"/health"})
    assert console[0].kind == "console"
    assert any(f.surface_path == "/health" for f in network)


def test_run_put_e2e_flow_passes_on_mock_client() -> None:
    client = MagicMock()
    client.get.return_value = _mock_response(status=200)
    client.request.return_value = _mock_response(
        status=200,
        json_body={"openapi": "3.0.0", "paths": {}},
    )
    with patch("orchestrator.put_e2e_runner.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = client
        result = run_put_e2e_flow("http://127.0.0.1:9", "crm", repo_root=REPO)
    assert result.verdict == "PASS"
    assert result.passed is True
    assert "/health" in result.exercised_paths
    assert result.capture.get("playwright_ready") is not None


def test_run_put_e2e_flow_fails_on_bad_status() -> None:
    client = MagicMock()
    client.get.return_value = _mock_response(status=500)
    with patch("orchestrator.put_e2e_runner.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = client
        result = run_put_e2e_flow("http://127.0.0.1:9", "crm", repo_root=REPO)
    assert result.verdict == "FAIL"
    assert result.passed is False
    assert any(f.kind == "step_fail" for f in result.findings)


def test_run_put_e2e_flow_unknown_id() -> None:
    result = run_put_e2e_flow("http://127.0.0.1:9", "missing_flow", repo_root=REPO)
    assert result.verdict == "FAIL"


def test_put_e2e_result_serializes() -> None:
    result = run_put_e2e_flow("http://127.0.0.1:1", "missing_flow", repo_root=REPO)
    payload = result.to_dict()
    json.dumps(payload)
