from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import (
    MaintenanceRefactorPassedPayload,
    MaintenanceRefactorStartedPayload,
)
from agent_core.models.events_records import (
    MaintenanceRefactorPassedEvent,
    MaintenanceRefactorStartedEvent,
)


def should_run_refactor_pass(slices_completed: int, every_n: int) -> bool:
    return every_n > 0 and slices_completed > 0 and slices_completed % every_n == 0


def run_maintenance_refactor(
    orch: Any,
    run_id: UUID,
    *,
    slices_completed: int,
    insert_fix_slices: bool = True,
) -> bool:
    store = orch._store
    store.append(
        MaintenanceRefactorStartedEvent(
            event_type=EventType.MAINTENANCE_REFACTOR_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MaintenanceRefactorStartedPayload(
                campaign_id=str(run_id),
                after_slice_count=slices_completed,
            ),
        ),
    )
    rows_for_index = store.list_run_events(str(run_id))
    from nimbusware_maker.workspace import resolve_run_workspace
    from nimbusware_orchestrator.orphan_index import build_orphan_report
    from nimbusware_orchestrator.similarity_index import build_similarity_index

    ws_index = resolve_run_workspace(rows_for_index)
    from nimbusware_orchestrator.code_intel_store import load_or_build_code_intel

    repo_root = getattr(orch, "repo_root", ws_index)
    intel = load_or_build_code_intel(Path(repo_root), ws_index)
    orphan_report = build_orphan_report(ws_index)
    similarity = build_similarity_index(ws_index)
    duplicate_clusters = [c for c in similarity.clusters if len(c.paths) > 1]
    reach = intel.get("route_reachability")
    unreachable_count = 0
    if isinstance(reach, dict):
        raw_n = reach.get("unreachable_count")
        if isinstance(raw_n, int) and not isinstance(raw_n, bool):
            unreachable_count = raw_n
    index_meta = {
        "orphan_count": len(orphan_report.orphans),
        "duplicate_clusters": len(duplicate_clusters),
        "unreachable_module_count": unreachable_count,
        "code_intel_persisted": True,
    }
    gate_fail = False
    if hasattr(orch, "_emit_refactor_stage_optional"):
        rows = store.list_run_events(str(run_id))
        wf = None
        for row in rows:
            if row.get("event_type") == EventType.RUN_CREATED.value:
                payload = row.get("payload")
                if isinstance(payload, dict):
                    wf = payload.get("workflow_profile")
                break
        gate_fail = bool(orch._emit_refactor_stage_optional(run_id, workflow_profile=wf))
    fix_slices = 0
    if insert_fix_slices and (gate_fail or orphan_report.orphans or duplicate_clusters):
        from agent_core.models.backlog import BacklogSlice
        from nimbusware_orchestrator.backlog_generator import (
            backlog_from_events,
            emit_backlog_revised,
        )

        rows = store.list_run_events(str(run_id))
        backlog = backlog_from_events(rows)
        if backlog is not None:
            target_paths: tuple[str, ...] = ("packages/",)
            rationale = "Refactor maintenance fix slice"
            if orphan_report.orphans:
                first = orphan_report.orphans[0]
                reason = orphan_report.orphan_metadata.get(first, "orphan")
                target_paths = (first,)
                rationale = f"Simplify orphan module: {first} ({reason})"
            elif duplicate_clusters:
                cluster = duplicate_clusters[0]
                if cluster.paths:
                    target_paths = (cluster.paths[0],)
                    rationale = f"Deduplicate similar code cluster ({cluster.hash})"
            fix = BacklogSlice(
                slice_id=f"fix-refactor-{slices_completed}",
                rationale=rationale,
                target_paths=target_paths,
            )
            epics = list(backlog.epics)
            if epics and epics[0].features:
                feat = epics[0].features[0]
                new_slices = tuple(list(feat.slices) + [fix])
                epics[0] = epics[0].model_copy(
                    update={
                        "features": (
                            feat.model_copy(update={"slices": new_slices}),
                            *epics[0].features[1:],
                        ),
                    },
                )
                revised = backlog.model_copy(update={"epics": tuple(epics)})
                emit_backlog_revised(store, run_id, revised, revision_reason="refactor_fix_slices")
                fix_slices = 1
    rows = store.list_run_events(str(run_id))
    from nimbusware_maker.workspace import resolve_run_workspace
    from nimbusware_orchestrator.factory_cadence import maybe_run_factory_cadence_pass
    from nimbusware_orchestrator.launch_evaluator import maybe_run_launch_eval_for_campaign

    ws = resolve_run_workspace(rows)
    maybe_run_launch_eval_for_campaign(
        store,
        run_id,
        rows,
        workspace=ws,
    )
    maybe_run_factory_cadence_pass(
        store,
        run_id,
        rows,
        workspace=ws,
        slices_completed=slices_completed,
        repo_root=getattr(orch, "repo_root", None),
    )
    store.append(
        MaintenanceRefactorPassedEvent(
            event_type=EventType.MAINTENANCE_REFACTOR_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"code_intel": index_meta},
            payload=MaintenanceRefactorPassedPayload(
                campaign_id=str(run_id),
                fix_slices_queued=fix_slices,
            ),
        ),
    )
    return not gate_fail
