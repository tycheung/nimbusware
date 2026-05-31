from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_orchestrator._pipeline._helpers import InMemoryEventStore
from hermes_orchestrator.registry import RoleRegistry


def default_paths(repo_root: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or Path(__file__).resolve().parents[3]
    return (
        root / "configs" / "model-routing.yaml",
        root / "configs" / "workflows" / "default.yaml",
    )


def make_dev_orchestrator(
    repo_root: Path | None = None,
    *,
    memory_chunk_store: Any | None = None,
    bundle_outcome_store: Any | None = None,
) -> tuple[Any, InMemoryEventStore]:
    from hermes_orchestrator.pipeline import RunOrchestrator

    root = repo_root or Path(__file__).resolve().parents[3]
    base, _ = default_paths(root)
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    mem = InMemoryEventStore()
    orch = RunOrchestrator(
        mem,
        reg,
        repo_root=root,
        base_config_path=base,
        memory_chunk_store=memory_chunk_store,
        bundle_outcome_store=bundle_outcome_store,
    )
    return orch, mem
