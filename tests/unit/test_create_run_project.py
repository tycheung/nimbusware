from __future__ import annotations

from pathlib import Path

import pytest

from env import find_repo_root
from maker.store import InMemoryProjectStore
from orchestrator.pipeline import make_dev_orchestrator


def test_create_run_with_project_metadata(tmp_path: Path) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    ws = tmp_path / "workspace"
    ws.mkdir()
    project = InMemoryProjectStore().create(name="Demo", workspace_path=str(ws))
    run_id = orch.create_run(
        "micro_slice",
        project_id=project.project_id,
        project_name=project.name,
        project_workspace_path=project.workspace_path,
        project_template=project.template,
    )
    rows = store.list_run_events(str(run_id))
    meta = rows[0].get("metadata") or {}
    assert meta.get("project", {}).get("id") == str(project.project_id)
    assert meta.get("project", {}).get("workspace_path") == str(ws.resolve())


def test_create_run_invalid_project_workspace_raises(tmp_path: Path) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, _store = make_dev_orchestrator(repo)
    from uuid import uuid4

    with pytest.raises(ValueError, match="not a directory"):
        orch.create_run(
            "default",
            project_id=uuid4(),
            project_name="Bad",
            project_workspace_path=str(tmp_path / "missing"),
        )
