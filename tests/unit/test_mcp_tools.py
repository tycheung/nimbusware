from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from nimbusware_mcp.tools import TOOL_SPECS, call_tool


def test_tool_specs_include_required_tools() -> None:
    names = {t["name"] for t in TOOL_SPECS}
    assert names == {
        "nimbusware_apply_slice",
        "nimbusware_maker_pending",
        "nimbusware_prepare_slice",
        "nimbusware_resume_campaign",
        "nimbusware_revert_workspace",
        "nimbusware_run_status",
        "nimbusware_run_theater",
        "nimbusware_skip_slice",
        "nimbusware_slice_diff",
        "nimbusware_approve_plan",
        "nimbusware_compact_run",
        "nimbusware_campaign_status",
        "nimbusware_pause_campaign",
        "nimbusware_backlog_summary",
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


def test_unknown_tool_raises() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        call_tool("nope", {"run_id": "x"})
