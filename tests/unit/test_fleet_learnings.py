from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from maker.models import ProjectRecord
from maker.store import InMemoryProjectStore
from orchestrator.diagnose_learn import learnings_dir
from orchestrator.fleet_learnings import search_fleet_learnings, workspaces_for_tenant


def _project(tenant_id: UUID, workspace: Path) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name="demo",
        workspace_path=str(workspace),
        template="attach",
        default_workflow_profile="micro_slice",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        tenant_id=tenant_id,
    )


def test_search_fleet_learnings_across_workspaces(tmp_path: Path) -> None:
    tenant = uuid4()
    ws_a = tmp_path / "a"
    ws_b = tmp_path / "b"
    ws_a.mkdir()
    ws_b.mkdir()
    (learnings_dir(ws_a) / "sql-timeout.md").write_text(
        "# SQL timeout\nretry with smaller batch",
        encoding="utf-8",
    )
    (learnings_dir(ws_b) / "other.md").write_text("# Other\nunrelated", encoding="utf-8")

    store = InMemoryProjectStore()
    store._projects[uuid4()] = _project(tenant, ws_a)
    store._projects[uuid4()] = _project(tenant, ws_b)

    workspaces = workspaces_for_tenant(store, tenant)
    hits = search_fleet_learnings(workspaces, "sql timeout")
    assert len(hits) == 1
    assert hits[0]["learning_id"] == "sql-timeout"
    assert "workspace" in hits[0]
