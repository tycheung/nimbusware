from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from nimbusware_mcp.tools import TOOL_SPECS, call_tool


def test_tool_specs_include_required_tools() -> None:
    names = {t["name"] for t in TOOL_SPECS}
    assert names == {
        "nimbusware_apply_slice",
        "nimbusware_chat_fork",
        "nimbusware_chat_graph",
        "nimbusware_chat_select_branch",
        "nimbusware_classify_intent",
        "nimbusware_interject",
        "nimbusware_maker_pending",
        "nimbusware_patch",
        "nimbusware_patch_from_selection",
        "nimbusware_prepare_slice",
        "nimbusware_resume_campaign",
        "nimbusware_revert_workspace",
        "nimbusware_run_status",
        "nimbusware_run_tests",
        "nimbusware_run_theater",
        "nimbusware_skip_slice",
        "nimbusware_slice_diff",
        "nimbusware_approve_plan",
        "nimbusware_compact_run",
        "nimbusware_campaign_status",
        "nimbusware_pause_campaign",
        "nimbusware_backlog_summary",
        "nimbusware_list_context_artifacts",
        "nimbusware_create_context_artifact",
        "nimbusware_insert_context_artifact",
        "nimbusware_factory_evidence",
        "nimbusware_replay_from",
        "nimbusware_launch_eval",
        "nimbusware_swap_role_model",
        "nimbusware_set_discipline",
        "nimbusware_update_agent_overlay",
    }


@patch("nimbusware_mcp.tools.get_json")
def test_nimbusware_maker_pending(mock_get: Any) -> None:
    mock_get.return_value = {"plan_approved": False, "pending": None}
    out = call_tool("nimbusware_maker_pending", {"run_id": "abc"})
    mock_get.assert_called_once_with("/runs/abc/maker/pending")
    assert "plan_approved" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_resume_campaign(mock_post: Any) -> None:
    mock_post.return_value = {"status": "resumed"}
    out = call_tool("nimbusware_resume_campaign", {"campaign_id": "camp-1"})
    mock_post.assert_called_once_with("/campaigns/camp-1/resume", {})
    assert "resumed" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.get_json")
def test_nimbusware_run_status(mock_get: Any) -> None:
    mock_get.return_value = {"run_id": "abc", "status": "running"}
    out = call_tool("nimbusware_run_status", {"run_id": "abc"})
    mock_get.assert_called_once_with("/runs/abc")
    assert out["content"][0]["type"] == "text"
    assert "running" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_approve_plan(mock_post: Any) -> None:
    mock_post.return_value = {"status": "approved"}
    out = call_tool("nimbusware_approve_plan", {"run_id": "abc"})
    mock_post.assert_called_once_with("/runs/abc/maker/plan/approve", {})
    assert "approved" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_apply_slice(mock_post: Any) -> None:
    mock_post.return_value = {"status": "applied"}
    out = call_tool("nimbusware_apply_slice", {"run_id": "abc", "slice_id": "s1"})
    mock_post.assert_called_once_with("/runs/abc/maker/slices/apply", {"slice_id": "s1"})
    assert "applied" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_prepare_slice(mock_post: Any) -> None:
    mock_post.return_value = {"status": "awaiting_approval"}
    out = call_tool("nimbusware_prepare_slice", {"run_id": "abc"})
    mock_post.assert_called_once_with("/runs/abc/maker/slices/prepare", {})
    assert "awaiting_approval" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_skip_slice(mock_post: Any) -> None:
    mock_post.return_value = {"status": "skipped"}
    out = call_tool("nimbusware_skip_slice", {"run_id": "abc", "slice_id": "s1"})
    mock_post.assert_called_once_with("/runs/abc/maker/slices/skip", {"slice_id": "s1"})
    assert "skipped" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_revert_workspace(mock_post: Any) -> None:
    mock_post.return_value = {"status": "reverted"}
    out = call_tool("nimbusware_revert_workspace", {"run_id": "abc"})
    mock_post.assert_called_once_with("/runs/abc/workspace/revert", {})
    assert "reverted" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_compact_run(mock_post: Any) -> None:
    mock_post.return_value = {"compacted": True, "tokens_before": 100, "tokens_after": 40}
    out = call_tool("nimbusware_compact_run", {"run_id": "abc"})
    mock_post.assert_called_once_with("/runs/abc/compact", {})
    assert "compacted" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_classify_intent(mock_post: Any) -> None:
    mock_post.return_value = {
        "classification": {"work_type": "patch", "confidence": 0.9, "suggested_profile": "patch"},
    }
    out = call_tool("nimbusware_classify_intent", {"message": "fix bug"})
    mock_post.assert_called_once()
    assert "patch" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_interject(mock_post: Any) -> None:
    mock_post.return_value = {"queue": {"count": 1}}
    out = call_tool("nimbusware_interject", {"run_id": "abc", "message": "[steer] smaller diff"})
    mock_post.assert_called_once_with(
        "/runs/abc/interjection-queue",
        {"message": "[steer] smaller diff", "priority": "next", "force_break": False},
    )
    assert "count" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_run_tests(mock_post: Any) -> None:
    mock_post.return_value = {"tests_passed": True, "exit_code": 0}
    out = call_tool("nimbusware_run_tests", {"run_id": "abc"})
    mock_post.assert_called_once_with("/runs/abc/maker/run-tests", {})
    assert "tests_passed" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.get_json")
@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_patch(mock_post: Any, mock_get: Any) -> None:
    mock_get.return_value = {"workspace_path": "/tmp/proj"}
    mock_post.side_effect = [
        {"run_id": "run-patch-1"},
        {"status": "started"},
        {"status": "micro_slice_recorded", "slices_completed": 1},
    ]
    out = call_tool(
        "nimbusware_patch",
        {"project_id": "proj-1", "message": "fix login", "failing_test": "tests/test_x.py"},
    )
    assert mock_post.call_count == 3
    create_body = mock_post.call_args_list[0][0][1]
    assert create_body["workflow_profile"] == "patch"
    assert "run-patch-1" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.get_json")
@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_patch_from_selection_alias(mock_post: Any, mock_get: Any) -> None:
    mock_get.return_value = {"workspace_path": "/tmp/proj"}
    mock_post.side_effect = [
        {"run_id": "run-sel-1"},
        {"status": "started"},
        {"status": "micro_slice_recorded"},
    ]
    out = call_tool(
        "nimbusware_patch_from_selection",
        {
            "project_id": "proj-1",
            "message": "fix test",
            "target_paths": ["src/a.py"],
            "stack_trace": "AssertionError",
        },
    )
    assert mock_post.call_count == 3
    create_body = mock_post.call_args_list[0][0][1]
    assert create_body["patch_context"]["target_paths"] == ["src/a.py"]
    assert "run-sel-1" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.get_json")
@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_patch_selects_go_profile(mock_post: Any, mock_get: Any, tmp_path: Any) -> None:
    ws = tmp_path / "go-proj"
    ws.mkdir()
    (ws / "go.mod").write_text("module example.com/x\n\ngo 1.21\n", encoding="utf-8")
    mock_get.return_value = {"workspace_path": str(ws)}
    mock_post.side_effect = [
        {"run_id": "run-go-1"},
        {"status": "started"},
        {"status": "micro_slice_recorded"},
    ]
    call_tool("nimbusware_patch", {"project_id": "proj-go", "message": "fix go test"})
    create_body = mock_post.call_args_list[0][0][1]
    assert create_body["workflow_profile"] == "patch_go"


@patch("nimbusware_mcp.tools.get_json")
def test_nimbusware_chat_graph(mock_get: Any) -> None:
    mock_get.return_value = {"session_id": "sess-1", "nodes": [], "edges": [], "branches": []}
    out = call_tool("nimbusware_chat_graph", {"session_id": "sess-1"})
    mock_get.assert_called_once_with("/chat/sessions/sess-1/graph")
    assert "sess-1" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.post_json")
def test_nimbusware_chat_fork(mock_post: Any) -> None:
    mock_post.return_value = {"active_leaf_turn_id": "turn-1"}
    out = call_tool("nimbusware_chat_fork", {"session_id": "sess-1", "turn_id": "turn-1"})
    mock_post.assert_called_once_with("/chat/sessions/sess-1/fork", {"turn_id": "turn-1"})
    assert "turn-1" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.put_response")
def test_nimbusware_chat_select_branch(mock_put: Any) -> None:
    mock_resp = mock_put.return_value
    mock_resp.json.return_value = {"leaf_turn_id": "turn-2"}
    out = call_tool(
        "nimbusware_chat_select_branch",
        {"session_id": "sess-1", "leaf_turn_id": "turn-2"},
    )
    mock_put.assert_called_once()
    assert "turn-2" in out["content"][0]["text"]


def test_unknown_tool_raises() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        call_tool("nope", {"run_id": "x"})


@patch("nimbusware_mcp.tools.put_response")
def test_nimbusware_set_discipline(mock_put: Any) -> None:
    mock_resp = mock_put.return_value
    mock_resp.json.return_value = {"user_id": "u1", "default_discipline": "backend"}
    out = call_tool("nimbusware_set_discipline", {"discipline": "backend"})
    mock_put.assert_called_once_with(
        "/users/me/discipline-profile",
        {"default_discipline": "backend"},
    )
    assert "backend" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.put_response")
def test_nimbusware_set_discipline_clear(mock_put: Any) -> None:
    mock_resp = mock_put.return_value
    mock_resp.json.return_value = {"user_id": "u1", "default_discipline": None}
    call_tool("nimbusware_set_discipline", {"discipline": ""})
    mock_put.assert_called_once_with("/users/me/discipline-profile", {"default_discipline": None})


@patch("nimbusware_mcp.tools.put_response")
def test_nimbusware_update_agent_overlay(mock_put: Any) -> None:
    mock_resp = mock_put.return_value
    mock_resp.json.return_value = {
        "user_id": "u1",
        "overlays": {"backend": {"prompt_extension": "thin handlers", "version": 1}},
    }
    out = call_tool(
        "nimbusware_update_agent_overlay",
        {"discipline": "backend", "prompt_extension": "thin handlers"},
    )
    mock_put.assert_called_once_with(
        "/users/me/agent-overlays/backend",
        {"prompt_extension": "thin handlers"},
    )
    assert "thin handlers" in out["content"][0]["text"]


@patch("nimbusware_mcp.tools.put_response")
def test_nimbusware_update_agent_overlay_clear(mock_put: Any) -> None:
    mock_resp = mock_put.return_value
    mock_resp.json.return_value = {"user_id": "u1", "overlays": {}}
    call_tool("nimbusware_update_agent_overlay", {"discipline": "backend", "clear": True})
    mock_put.assert_called_once_with(
        "/users/me/agent-overlays/backend",
        {"prompt_extension": None, "custom_agent_id": None},
    )
