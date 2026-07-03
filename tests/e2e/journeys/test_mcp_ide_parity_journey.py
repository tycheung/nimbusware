from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from e2e.harness.workspace import copy_fixture_repo
from mcp.tools import call_tool

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


@pytest.fixture
def mcp_http(journey_client, monkeypatch: pytest.MonkeyPatch):
    client = journey_client.client

    def _get_json(path: str) -> Any:
        resp = client.get(f"/v1{path}")
        assert resp.status_code < 400, resp.text
        return resp.json()

    def _post_json(path: str, body: dict[str, Any] | None = None) -> Any:
        resp = client.post(f"/v1{path}", json=body or {})
        assert resp.status_code < 400, resp.text
        return resp.json()

    def _put_response(path: str, body: dict[str, Any]) -> Any:
        resp = client.put(f"/v1{path}", json=body)
        assert resp.status_code < 400, resp.text
        return resp

    monkeypatch.setattr("mcp.tools.get_json", _get_json)
    monkeypatch.setattr("mcp.tools.post_json", _post_json)
    monkeypatch.setattr("mcp.tools.put_response", _put_response)


def test_mcp_classify_patch_and_chat_graph_round_trip(
    journey_client,
    mcp_http,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "mcp-ws")
    journey_client.attach_project(ws, name="MCP-parity")
    project_id = journey_client.project_id
    assert project_id

    classified = call_tool(
        "nimbusware_classify_intent",
        {"message": "fix failing unit test in calculator"},
    )
    assert "patch" in classified["content"][0]["text"].lower()

    session_resp = journey_client.client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id},
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    turn_resp = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "fix failing test"},
    )
    assert turn_resp.status_code == 200
    turn_id = turn_resp.json()["message"]["turn_id"]

    forked = call_tool(
        "nimbusware_chat_fork",
        {"session_id": session_id, "turn_id": turn_id},
    )
    assert turn_id in forked["content"][0]["text"]

    graph = call_tool("nimbusware_chat_graph", {"session_id": session_id})
    assert session_id in graph["content"][0]["text"]

    patched = call_tool(
        "nimbusware_patch",
        {
            "project_id": project_id,
            "message": "fix calculator test",
            "failing_test": "tests/test_calculator.py",
        },
    )
    patch_payload = json.loads(patched["content"][0]["text"])
    run_id = str(patch_payload.get("run_id") or "")
    assert run_id

    interject = call_tool(
        "nimbusware_interject",
        {"run_id": run_id, "message": "[steer] smaller diff"},
    )
    assert (
        "count" in interject["content"][0]["text"].lower()
        or "queue" in interject["content"][0]["text"].lower()
    )
