from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.runtime import AgentStep
from client.http import admin_headers, api_base, user_headers
from maker.readiness import build_platform_readiness
from maker.slice_preview import (
    preview_note_for_scoped_mode,
    unified_diff_from_edits,
)
from maker.store import InMemoryProjectStore
from projections.builders.maker_progress import maker_progress_from_events
from projections.builders.run_escalated import run_escalated_timeline_summary
from store.memory import InMemoryEventStore


def test_slice_preview_unified_diff(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.py").write_text("old\n", encoding="utf-8")
    diff = unified_diff_from_edits(
        ws,
        [{"path": "a.py", "content": "new\n"}],
    )
    assert "a.py" in diff
    assert preview_note_for_scoped_mode(["a.py", "b.py"]) != ""


def test_readiness_missing_config_reports_fail(tmp_path: Path) -> None:
    body = build_platform_readiness(
        repo_root=tmp_path,
        store=InMemoryEventStore(),
    )
    assert body["checks"]["repo_root"]["status"] == "fail"


def test_maker_project_store_list_roundtrip(tmp_path: Path) -> None:
    store = InMemoryProjectStore()
    ws = tmp_path / "app"
    ws.mkdir()
    rec = store.create(name="T", workspace_path=str(ws))
    listed = store.list()
    assert any(p.project_id == rec.project_id for p in listed)


def test_maker_progress_projection_minimal() -> None:
    body = maker_progress_from_events(
        [
            {
                "event_type": "run.created",
                "payload": {"workflow_profile": "default"},
            },
        ],
    )
    assert "current_headline" in body


def test_run_escalated_summary_empty() -> None:
    assert run_escalated_timeline_summary([]) is None


def test_client_helpers() -> None:
    assert api_base().endswith("/v1")
    assert "X-Nimbusware-Admin-Token" in admin_headers()
    assert isinstance(user_headers(), dict)


def test_agent_step_dataclass() -> None:
    step = AgentStep(tool="read_file", arguments={"path": "x.py"})
    assert step.tool == "read_file"


def test_readiness_with_full_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    cfg = tmp_path / "configs"
    cfg.mkdir()
    (cfg / "model-routing.yaml").write_text(
        "runtime:\n  base_url: http://127.0.0.1:11434\nmodels:\n  primary:\n    id: tiny\n",
        encoding="utf-8",
    )
    (cfg / "roles.yaml").write_text("roles: []\n", encoding="utf-8")
    body = build_platform_readiness(repo_root=tmp_path, store=InMemoryEventStore())
    assert body["checks"]["repo_root"]["status"] == "ok"
