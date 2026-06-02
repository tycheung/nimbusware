from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StitchAppliedEvent,
    StitchAppliedPayload,
    StitchFailedEvent,
    StitchFailedPayload,
    StitchPlanEmittedEvent,
    StitchPlanEmittedPayload,
)
from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.registry import RoleRegistry
from hermes_research.stages import _emit_critique_panel
from hermes_research.stitch_manifests import persist_transplant_manifest
from hermes_research.stitch_models import TransplantManifest
from hermes_research.stitch_read_model import has_code_research_brief
from hermes_store.protocol import EventStore
from nimbusware_maker.workspace import workspace_path_from_run_created_metadata
from nimbusware_maker.workspace_snapshot import create_workspace_snapshot

STITCH_CRITIQUE_STAGE = "stitcher.critique"
_STUB_TARGET_PATHS = (
    "packages/stub_transplant/__init__.py",
    "packages/stub_transplant/auth_helpers.py",
)


def _stub_manifest(manifest_id: str) -> TransplantManifest:
    return TransplantManifest(
        manifest_id=manifest_id,
        source_kind="stub",
        source_tree_hash=f"stub:{manifest_id[:8]}",
        file_paths=_STUB_TARGET_PATHS,
        license_paths=("LICENSE",),
        required_env_vars=(),
    )


def _count_loc(paths: tuple[str, ...], workspace: Path) -> int:
    total = 0
    for rel in paths:
        path = workspace / rel
        if path.is_file():
            try:
                total += len(path.read_text(encoding="utf-8").splitlines())
            except OSError:
                pass
    return total


def _apply_stub_transplant(workspace: Path, paths: tuple[str, ...]) -> list[str]:
    added: list[str] = []
    for rel in paths:
        target = workspace / rel
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("__init__.py"):
            body = '"""Stub transplant package (CI-safe)."""\n'
        else:
            body = "# Stub transplant module (CI-safe).\n"
        target.write_text(body, encoding="utf-8")
        added.append(rel)
    return added


def emit_stitch_stages_stub(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    repo_root: Path,
    run_created_metadata: dict[str, Any],
    stitch_meta: dict[str, Any],
    prior_events: list[dict[str, Any]],
) -> bool:
    """Emit stitch plan/apply (or failed). Returns True if stitch.applied was emitted."""
    if not has_code_research_brief(prior_events):
        return False

    max_files = int(stitch_meta.get("max_files", 40) or 40)
    max_loc = int(stitch_meta.get("max_loc", 2500) or 2500)
    max_deps = int(stitch_meta.get("max_new_dependencies", 10) or 10)

    manifest_id = str(uuid4())
    manifest = _stub_manifest(manifest_id)
    target_paths = list(manifest.file_paths)

    if len(target_paths) > max_files:
        store.append(
            StitchFailedEvent(
                event_type=EventType.STITCH_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("stitcher"),
                payload=StitchFailedPayload(
                    reason_code="budget_max_files",
                    rollback_snapshot_ref=None,
                ),
            ),
        )
        return False

    persist_transplant_manifest(repo_root, manifest)
    store.append(
        StitchPlanEmittedEvent(
            event_type=EventType.STITCH_PLAN_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=registry.resolve("stitcher"),
            payload=StitchPlanEmittedPayload(
                target_paths=target_paths,
                source_manifest_id=manifest_id,
                wiring_delta_summary=(
                    "Stub transplant: add minimal auth helper modules from indexed pattern."
                ),
            ),
        ),
    )
    _emit_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        stage_name=STITCH_CRITIQUE_STAGE,
        producer_key="stitcher",
    )

    workspace = workspace_path_from_run_created_metadata(run_created_metadata)
    if workspace is None or not workspace.is_dir():
        store.append(
            StitchFailedEvent(
                event_type=EventType.STITCH_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("stitcher"),
                payload=StitchFailedPayload(
                    reason_code="workspace_missing",
                    rollback_snapshot_ref=None,
                ),
            ),
        )
        return False

    snapshot = create_workspace_snapshot(
        workspace,
        run_id=str(run_id),
        label="pre_stitch_apply",
        paths=target_paths,
    )
    snapshot_ref = str(snapshot.get("snapshot_id") or "")

    projected_loc = _count_loc(manifest.file_paths, workspace) + 2 * len(target_paths)
    if projected_loc > max_loc:
        store.append(
            StitchFailedEvent(
                event_type=EventType.STITCH_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("stitcher"),
                payload=StitchFailedPayload(
                    reason_code="budget_max_loc",
                    rollback_snapshot_ref=snapshot_ref or None,
                ),
            ),
        )
        return False

    deps_added = ["stub-transplant-runtime"] if max_deps > 0 else []
    if len(deps_added) > max_deps:
        store.append(
            StitchFailedEvent(
                event_type=EventType.STITCH_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("stitcher"),
                payload=StitchFailedPayload(
                    reason_code="budget_max_new_dependencies",
                    rollback_snapshot_ref=snapshot_ref or None,
                ),
            ),
        )
        return False

    files_added = _apply_stub_transplant(workspace, manifest.file_paths)
    store.append(
        StitchAppliedEvent(
            event_type=EventType.STITCH_APPLIED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=registry.resolve("stitcher"),
            metadata={"workspace_snapshot": snapshot},
            payload=StitchAppliedPayload(
                snapshot_ref=snapshot_ref,
                files_added=files_added,
                deps_added=deps_added,
            ),
        ),
    )
    return True
