from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.dev_env_policy import (
    human_fidelity_profile_enabled,
    persistent_dev_env_enabled,
)
from orchestrator.simplification_rubric_critique import (
    emit_simplification_rubric_stage,
    run_simplification_rubric,
)
from orchestrator.workflow_blocks_simple import (
    dev_env_effective_metadata,
    parse_dev_env_workflow_block,
)
from store.memory import InMemoryEventStore

ROOT = find_repo_root()


def test_parse_dev_env_workflow_block_fullstack() -> None:
    block = parse_dev_env_workflow_block(ROOT, "micro_slice_fullstack")
    assert block.enabled is True
    assert block.human_fidelity_enabled is True
    assert block.ui_controller_enabled is True
    meta = dev_env_effective_metadata(block)
    assert meta["human_fidelity_enabled"] is True


def test_human_fidelity_profile_enabled_from_frozen_metadata() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "dev_env_effective": {
                    "enabled": True,
                    "human_fidelity_enabled": True,
                },
            },
        },
    ]
    assert human_fidelity_profile_enabled(rows) is True
    assert persistent_dev_env_enabled(rows) is True


def test_simplification_rubric_passes_healthy_repo(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")
    result = run_simplification_rubric(tmp_path, health_floor=10.0)
    assert result.passed is True
    assert result.inventory.health_score >= 10.0


def test_emit_simplification_rubric_stage(tmp_path: Path) -> None:
    from uuid import uuid4

    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    store = InMemoryEventStore()
    run_id = uuid4()
    emit_simplification_rubric_stage(store, run_id, tmp_path, health_floor=1.0)
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert "stage.started" in types
    assert "stage.passed" in types
