from __future__ import annotations

from uuid import uuid4

from orchestrator.collab.mesh_context import (
    clear_mesh_binding_context,
    mesh_actor_user_id,
    mesh_participant_overrides,
)
from orchestrator.collab.mesh_hydrate import (
    ensure_mesh_binding_for_llm,
    hydrate_mesh_binding_from_run,
    set_active_run_for_mesh,
)


def test_ensure_mesh_binding_noop_without_run() -> None:
    clear_mesh_binding_context()
    set_active_run_for_mesh(None)
    ensure_mesh_binding_for_llm()
    assert mesh_participant_overrides() is None


def test_hydrate_mesh_binding_from_run_missing_session() -> None:
    clear_mesh_binding_context()
    ok = hydrate_mesh_binding_from_run(uuid4())
    assert ok is False
    assert mesh_participant_overrides() is None
    assert mesh_actor_user_id() == ""
