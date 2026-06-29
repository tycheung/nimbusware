from __future__ import annotations

from uuid import uuid4

from nimbusware_orchestrator.collab_parallel_slices import collab_mesh_parallel_count


class _CollabRow:
    def __init__(self, discipline: str | None) -> None:
        self.user_discipline = discipline


class _CollabStore:
    def __init__(self, rows: list[_CollabRow]) -> None:
        self._rows = rows

    def list_participants(self, _session_id) -> list[_CollabRow]:
        return self._rows


class _Store:
    def list_run_events(self, _run_id: str) -> list[dict]:
        return []


def test_collab_parallel_requires_two_disciplines(monkeypatch) -> None:
    run_id = uuid4()
    session_id = uuid4()
    node_ids = [uuid4(), uuid4()]

    monkeypatch.setattr(
        "nimbusware_orchestrator.collab_parallel_slices.resolve_mesh_context_for_run",
        lambda _rid: (session_id, "auto_share", node_ids),
    )
    collab = _CollabStore([_CollabRow("frontend"), _CollabRow("backend")])
    assert collab_mesh_parallel_count(run_id, store=_Store(), collab_store=collab) == 2


def test_collab_parallel_single_discipline_stays_serial(monkeypatch) -> None:
    run_id = uuid4()
    session_id = uuid4()
    node_ids = [uuid4(), uuid4()]

    monkeypatch.setattr(
        "nimbusware_orchestrator.collab_parallel_slices.resolve_mesh_context_for_run",
        lambda _rid: (session_id, "auto_share", node_ids),
    )
    collab = _CollabStore([_CollabRow("frontend"), _CollabRow(None)])
    assert collab_mesh_parallel_count(run_id, store=_Store(), collab_store=collab) == 1
