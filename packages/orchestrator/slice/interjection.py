from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from orchestrator.interjection_queue import InterjectionItem, queue_for_run
from orchestrator.interjection_slo import INTERJECTION_ENQUEUED_STAGE
from orchestrator.slice.gate import SliceGateChainResult, SliceGateStep
from orchestrator.slice.micro_slice import SlicePlan


@dataclass
class InterjectionCycle:
    items: list[InterjectionItem] = field(default_factory=list)
    force_break: bool = False
    build_from_chat: bool = False
    patch_from_chat: bool = False
    steer_from_chat: bool = False
    skip_slice: bool = False

    @property
    def messages(self) -> list[str]:
        return [i.message for i in self.items if i.message.strip()]

    @property
    def plain_messages(self) -> list[str]:
        return [
            i.message
            for i in self.items
            if i.message.strip() and not (i.patch_from_chat or i.steer_from_chat or i.skip_slice)
        ]


def emit_interjection_enqueued(
    store: Any,
    run_id: UUID | str,
    item: InterjectionItem,
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "interjection": {
                    "message": item.message[:500],
                    "priority": item.priority.value,
                    "patch_from_chat": item.patch_from_chat,
                    "steer_from_chat": item.steer_from_chat,
                    "skip_slice": item.skip_slice,
                    "build_from_chat": item.build_from_chat,
                    "discipline": item.discipline,
                    "taxonomy_key": item.taxonomy_key,
                    "surface_id": item.surface_id,
                    "routed_from_user_id": item.routed_from_user_id,
                },
            },
            payload=StageStartedPayload(stage_name=INTERJECTION_ENQUEUED_STAGE, attempt=1),
        ),
    )


def emit_interjection_drained(
    store: Any,
    run_id: UUID | str,
    cycle: InterjectionCycle,
) -> None:
    if not cycle.items:
        return
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "interjection": {
                    "count": len(cycle.items),
                    "force_break": cycle.force_break,
                    "build_from_chat": cycle.build_from_chat,
                    "patch_from_chat": cycle.patch_from_chat,
                    "steer_from_chat": cycle.steer_from_chat,
                    "skip_slice": cycle.skip_slice,
                    "messages": cycle.messages[:10],
                }
            },
            payload=StageStartedPayload(stage_name="interjection.drained", attempt=1),
        ),
    )


def _project_from_run_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        project = meta.get("project")
        return project if isinstance(project, dict) else None
    return None


def emit_build_from_chat_campaign(
    store: Any,
    run_id: UUID | str,
    *,
    campaign_run_id: str,
    source_messages: list[str],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "interjection": {
                    "build_from_chat": True,
                    "campaign_run_id": campaign_run_id,
                    "messages": source_messages[:5],
                },
            },
            payload=StagePassedPayload(stage_name="interjection.build_from_chat", duration_ms=0),
        ),
    )


def handle_build_from_chat_interjection(
    orch: Any,
    run_id: UUID | str,
    cycle: InterjectionCycle,
    rows: list[dict[str, Any]],
) -> str | None:
    if not cycle.build_from_chat:
        return None
    from orchestrator.campaign.campaign import campaign_enabled_for_run

    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if campaign_enabled_for_run(rows):
        from maker.workspace.workspace import resolve_run_workspace

        ws = resolve_run_workspace(rows)
        orch.start_campaign(rid, workspace=ws)
        emit_build_from_chat_campaign(
            orch._store,
            rid,
            campaign_run_id=str(rid),
            source_messages=cycle.messages,
        )
        return str(rid)

    project = _project_from_run_rows(rows)
    if project is None or not str(project.get("id") or "").strip():
        emit_build_from_chat_campaign(
            orch._store,
            rid,
            campaign_run_id="",
            source_messages=cycle.messages,
        )
        return None

    prompt = "\n".join(cycle.messages)[:4000] or "Build from operator chat"
    requirements = {"business_prompt": prompt, "clarifications": []}
    meta = rows[0].get("metadata") if rows else {}
    requirements_block = meta.get("requirements") if isinstance(meta, dict) else None
    if isinstance(requirements_block, dict):
        base_prompt = str(requirements_block.get("business_prompt") or "").strip()
        if base_prompt:
            requirements["business_prompt"] = f"{base_prompt}\n\nOperator build request:\n{prompt}"

    from pathlib import Path
    from uuid import UUID as _UUID

    workspace_path = str(project.get("workspace_path") or "")
    new_run_id = orch.create_run(
        "campaign_micro_slice",
        project_id=_UUID(str(project["id"])),
        project_name=str(project.get("name") or project["id"]),
        project_workspace_path=workspace_path,
        project_template=str(project.get("template") or "attach"),
        requirements=requirements,
        autonomous=True,
    )
    attach_ws: Path | None = Path(workspace_path) if workspace_path else None
    orch.start_campaign(new_run_id, workspace=attach_ws, autonomous=True)
    emit_build_from_chat_campaign(
        orch._store,
        rid,
        campaign_run_id=str(new_run_id),
        source_messages=cycle.messages,
    )
    return str(new_run_id)


def process_interjection_cycle(store: Any, run_id: UUID | str) -> InterjectionCycle:
    q = queue_for_run(str(run_id))
    items = q.drain()
    cycle = InterjectionCycle(
        items=items,
        force_break=any(i.force_break for i in items),
        build_from_chat=any(i.build_from_chat for i in items),
        patch_from_chat=any(i.patch_from_chat for i in items),
        steer_from_chat=any(i.steer_from_chat for i in items),
        skip_slice=any(i.skip_slice for i in items),
    )
    emit_interjection_drained(store, run_id, cycle)
    return cycle


def steer_excerpt_from_cycle(cycle: InterjectionCycle) -> str:
    lines: list[str] = []
    for item in cycle.items:
        if item.steer_from_chat and item.message.strip():
            prefix = f"[{item.surface_id}] " if item.surface_id else ""
            lines.append(f"{prefix}{item.message.strip()}")
    return "\n".join(lines)[:4000]


def apply_surface_steer_to_plan(
    plan: SlicePlan,
    cycle: InterjectionCycle,
    *,
    manifest: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> SlicePlan:
    surface_id: str | None = None
    for item in reversed(cycle.items):
        if item.steer_from_chat and item.surface_id:
            surface_id = item.surface_id
            break
    if not surface_id:
        return plan
    stack_id = plan.stack_id
    if manifest and not stack_id:
        from orchestrator.stack.catalog import stack_for_surface

        stack = stack_for_surface(manifest, surface_id, repo_root=repo_root)
        if stack is not None:
            stack_id = stack.stack_id
    rationale = plan.rationale
    if surface_id != plan.surface_id:
        rationale = f"{plan.rationale}\n\nSurface steer: active surface → {surface_id}".strip()
    return SlicePlan(
        slice_id=plan.slice_id,
        rationale=rationale[:4000],
        target_paths=plan.target_paths,
        acceptance_criteria=plan.acceptance_criteria,
        surface_id=surface_id,
        stack_id=stack_id or plan.stack_id,
    )


def _infer_patch_target_paths(prompt: str, rows: list[dict[str, Any]]) -> tuple[str, ...]:
    from maker.intent.classifier import _infer_paths

    extracted = _infer_paths(prompt, {})
    if extracted:
        return tuple(extracted[:2])
    patch_ctx = None
    if rows:
        meta = rows[0].get("metadata")
        if isinstance(meta, dict):
            from orchestrator.patch_context import normalize_patch_context

            patch_ctx = normalize_patch_context(meta.get("patch_context"))
    if patch_ctx:
        paths = patch_ctx.get("target_paths")
        if isinstance(paths, list) and paths:
            return tuple(str(p) for p in paths[:2])
    return ("packages/",)


def emit_patch_from_chat_slice(
    store: Any,
    run_id: UUID | str,
    *,
    slice_id: str,
    source_messages: list[str],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "interjection": {
                    "patch_from_chat": True,
                    "backlog_slice_id": slice_id,
                    "messages": source_messages[:5],
                },
            },
            payload=StagePassedPayload(stage_name="interjection.patch_from_chat", duration_ms=0),
        ),
    )


def handle_patch_from_chat_interjection(
    store: Any,
    run_id: UUID | str,
    cycle: InterjectionCycle,
    rows: list[dict[str, Any]],
) -> str | None:
    patch_messages = [i.message for i in cycle.items if i.patch_from_chat and i.message.strip()]
    if not patch_messages:
        return None
    prompt = "\n".join(patch_messages)[:4000] or "Operator patch request"
    from agent_core.models.backlog import BacklogSlice, sync_backlog_metadata
    from orchestrator.campaign.generator import backlog_from_events, emit_backlog_revised

    slice_id = f"patch-{uuid4().hex[:8]}"
    patch_slice = BacklogSlice(
        slice_id=slice_id,
        rationale=f"Operator patch request:\n{prompt}",
        target_paths=_infer_patch_target_paths(prompt, rows),
    )
    backlog = backlog_from_events(rows)
    if backlog is not None and backlog.epics and backlog.epics[0].features:
        feat = backlog.epics[0].features[0]
        epics = list(backlog.epics)
        new_slices = tuple([patch_slice, *feat.slices])
        epics[0] = epics[0].model_copy(
            update={
                "features": (
                    feat.model_copy(update={"slices": new_slices}),
                    *epics[0].features[1:],
                ),
            },
        )
        revised = sync_backlog_metadata(backlog.model_copy(update={"epics": tuple(epics)}))
        emit_backlog_revised(store, run_id, revised, revision_reason="interjection_patch_from_chat")
    emit_patch_from_chat_slice(
        store,
        run_id,
        slice_id=slice_id,
        source_messages=patch_messages,
    )
    return slice_id


def handle_skip_slice_interjection(
    store: Any,
    run_id: UUID | str,
    cycle: InterjectionCycle,
    rows: list[dict[str, Any]],
) -> None:
    if not cycle.skip_slice:
        return
    from agent_core.models.backlog import SliceStatus, sync_backlog_metadata
    from orchestrator.campaign.generator import backlog_from_events, emit_backlog_revised
    from orchestrator.campaign.slice_selector import select_next_slice

    backlog = backlog_from_events(rows)
    if backlog is None:
        return
    selected = select_next_slice(backlog)
    if selected is None:
        return
    deferred_id = selected.slice.slice_id
    epics = list(backlog.epics)
    updated = False
    for ei, epic in enumerate(epics):
        features = list(epic.features)
        for fi, feature in enumerate(features):
            slices = list(feature.slices)
            for si, sl in enumerate(slices):
                if sl.slice_id != deferred_id:
                    continue
                slices[si] = sl.model_copy(update={"status": SliceStatus.DEFERRED})
                features[fi] = feature.model_copy(update={"slices": tuple(slices)})
                epics[ei] = epic.model_copy(update={"features": tuple(features)})
                updated = True
                break
    if updated:
        revised = sync_backlog_metadata(backlog.model_copy(update={"epics": tuple(epics)}))
        emit_backlog_revised(store, run_id, revised, revision_reason="interjection_skip_slice")


def apply_interjection_to_plan(plan: SlicePlan, cycle: InterjectionCycle) -> SlicePlan:
    if not cycle.plain_messages:
        return plan
    block = "\n".join(f"- {m}" for m in cycle.plain_messages[:5])
    rationale = f"{plan.rationale}\n\nOperator interjection:\n{block}"
    return SlicePlan(
        slice_id=plan.slice_id,
        target_paths=plan.target_paths,
        rationale=rationale[:4000],
        acceptance_criteria=plan.acceptance_criteria,
        surface_id=plan.surface_id,
        stack_id=plan.stack_id,
    )


def gate_result_for_force_break(plan: SlicePlan) -> SliceGateChainResult:
    steps = (
        SliceGateStep("interjection.force_break", "FAIL", "operator force break"),
        SliceGateStep("slice.gate", "FAIL", "paused"),
    )
    return SliceGateChainResult(
        slice_id=plan.slice_id,
        passed=False,
        steps=steps,
        status="paused_for_operator",
    )


def gate_result_for_skip_slice(plan: SlicePlan) -> SliceGateChainResult:
    steps = (SliceGateStep("interjection.skip_slice", "PASS", "operator skip/defer"),)
    return SliceGateChainResult(
        slice_id=plan.slice_id,
        passed=True,
        steps=steps,
        status="skipped_by_operator",
    )
