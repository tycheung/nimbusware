from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.refactor_stage import emit_refactor_stage_and_critique
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.workflow_refactor import RefactorWorkflowBlock
from nimbusware_store.memory import InMemoryEventStore

_REPO = Path(__file__).resolve().parents[2]


def test_refactor_stage_emits_loc_accord_metadata(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    for idx in range(20):
        (ws / f"module_{idx}.py").write_text("x = 1\n" * 30, encoding="utf-8")
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_REPO / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _REPO / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()
    failed = emit_refactor_stage_and_critique(
        store,
        registry,
        router,
        run_id=run_id,
        block=RefactorWorkflowBlock(enabled=True),
        workspace=ws,
    )
    assert failed is False
    started = [
        row
        for row in store.list_run_events(str(run_id))
        if row.get("event_type") == "stage.started"
    ]
    assert started
    meta = started[0].get("metadata") or {}
    refactor = meta.get("refactor") or {}
    assert refactor.get("loc_total", 0) > 0
    assert "loc_accord" in refactor
