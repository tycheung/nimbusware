from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from orchestrator.repo_intel.explorer import RepoExploreFinding, RepoExploreResult
from orchestrator.slice.cycle_integration import maybe_run_repo_explore_slice_stage


def test_sparse_graph_finding_does_not_revise_backlog(
    tmp_path: Path, monkeypatch
) -> None:
    store = MagicMock()
    store.list_run_events.return_value = []
    monkeypatch.setattr(
        "orchestrator.slice.cycle_integration.run_repo_explore",
        lambda _ws: RepoExploreResult(
            findings=[
                RepoExploreFinding(
                    kind="sparse_graph",
                    message="Code graph has very few nodes",
                )
            ]
        ),
    )
    emitted: list[object] = []
    monkeypatch.setattr(
        "orchestrator.slice.cycle_integration.emit_repo_explore",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "orchestrator.campaign.generator.emit_backlog_revised",
        lambda *a, **k: emitted.append((a, k)),
    )

    ok = maybe_run_repo_explore_slice_stage(
        store, uuid4(), tmp_path, slice_index=1
    )
    assert ok is True
    assert emitted == []
    store.list_run_events.assert_not_called()
