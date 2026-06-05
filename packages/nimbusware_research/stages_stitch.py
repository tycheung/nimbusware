from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    RoleId,
    StitchAppliedEvent,
    StitchAppliedPayload,
    StitchDependencyCheckedEvent,
    StitchDependencyCheckedPayload,
    StitchFailedEvent,
    StitchFailedPayload,
    StitchLicenseCheckedEvent,
    StitchLicenseCheckedPayload,
    StitchPlanEmittedEvent,
    StitchPlanEmittedPayload,
)
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_maker.workspace import workspace_path_from_run_created_metadata
from nimbusware_maker.workspace_snapshot import create_workspace_snapshot
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_research.stages import _emit_critique_panel
from nimbusware_research.stitch_manifests import persist_transplant_manifest
from nimbusware_research.stitch_models import TransplantManifest
from nimbusware_research.stitch_read_model import has_code_research_brief
from nimbusware_research.stitch_verifiers import (
    dependency_diff_check,
    license_check_passes,
    scan_manifest_licenses,
)
from nimbusware_store.protocol import EventStore

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


def _stitch_actor(registry: RoleRegistry) -> RoleId:
    return registry.resolve("stitcher")


def _append_stitch_failed(
    store: EventStore,
    registry: RoleRegistry,
    *,
    run_id: UUID,
    reason_code: str,
    rollback_snapshot_ref: str | None = None,
) -> None:
    store.append(
        StitchFailedEvent(
            event_type=EventType.STITCH_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=_stitch_actor(registry),
            payload=StitchFailedPayload(
                reason_code=reason_code,
                rollback_snapshot_ref=rollback_snapshot_ref,
            ),
        ),
    )


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
        _append_stitch_failed(store, registry, run_id=run_id, reason_code="budget_max_files")
        return False

    persist_transplant_manifest(repo_root, manifest)

    allowlist_raw = stitch_meta.get("license_allowlist")
    if isinstance(allowlist_raw, list) and allowlist_raw:
        allowlist = tuple(str(x).strip() for x in allowlist_raw if str(x).strip())
    else:
        allowlist = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause")

    detected = scan_manifest_licenses(
        manifest,
        repo_root,
        prior_events=prior_events,
    )
    license_result = license_check_passes(detected, allowlist)
    store.append(
        StitchLicenseCheckedEvent(
            event_type=EventType.STITCH_LICENSE_CHECKED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=_stitch_actor(registry),
            payload=StitchLicenseCheckedPayload(
                detected_licenses=list(license_result.detected_licenses),
                allowlist=list(license_result.allowlist),
                passed=license_result.passed,
                evidence_refs=list(license_result.evidence_refs),
            ),
        ),
    )
    if not license_result.passed:
        _append_stitch_failed(store, registry, run_id=run_id, reason_code="license_not_allowed")
        return False

    workspace = workspace_path_from_run_created_metadata(run_created_metadata)
    proposed_deps = ["stub-transplant-runtime"] if max_deps > 0 else []
    dep_result = dependency_diff_check(
        proposed_deps,
        max_new_dependencies=max_deps,
        workspace=workspace if workspace is not None else None,
    )
    store.append(
        StitchDependencyCheckedEvent(
            event_type=EventType.STITCH_DEPENDENCY_CHECKED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=_stitch_actor(registry),
            payload=StitchDependencyCheckedPayload(
                declared_deps=list(dep_result.declared_deps),
                new_deps=list(dep_result.new_deps),
                max_allowed=dep_result.max_allowed,
                passed=dep_result.passed,
                reason_code=dep_result.reason_code,
            ),
        ),
    )
    if not dep_result.passed:
        _append_stitch_failed(
            store,
            registry,
            run_id=run_id,
            reason_code="dependency_delta_rejected",
        )
        return False

    store.append(
        StitchPlanEmittedEvent(
            event_type=EventType.STITCH_PLAN_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=_stitch_actor(registry),
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

    if workspace is None or not workspace.is_dir():
        _append_stitch_failed(store, registry, run_id=run_id, reason_code="workspace_missing")
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
        _append_stitch_failed(
            store,
            registry,
            run_id=run_id,
            reason_code="budget_max_loc",
            rollback_snapshot_ref=snapshot_ref or None,
        )
        return False

    deps_added = list(proposed_deps)
    files_added = _apply_stub_transplant(workspace, manifest.file_paths)
    store.append(
        StitchAppliedEvent(
            event_type=EventType.STITCH_APPLIED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=_stitch_actor(registry),
            metadata={"workspace_snapshot": snapshot},
            payload=StitchAppliedPayload(
                snapshot_ref=snapshot_ref,
                files_added=files_added,
                deps_added=deps_added,
            ),
        ),
    )
    return True
