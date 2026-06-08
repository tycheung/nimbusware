"""Automatic factory tier checks on campaign maintenance cadence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from agent_core.models.events_records import StagePassedEvent, StageStartedEvent
from agent_core.read.campaign import campaign_effective_from_rows
from nimbusware_orchestrator.factory_completion import (
    FactoryGateResult,
    FactoryTier,
    evaluate_factory_gates,
    handle_put_e2e_failure,
    resolve_factory_tier,
)
from nimbusware_orchestrator.put_e2e_runner import (
    PutE2EResult,
    match_factory_flow_id,
    run_put_e2e_flow,
)

FACTORY_CADENCE_STAGE = "factory.cadence"
FACTORY_COMPLETE_STAGE = "factory.complete"


@dataclass(frozen=True)
class FactoryCompletionPolicy:
    factory_tier: FactoryTier = "T1"
    e2e_on_every_n_slices: int = 5
    auto_launch_eval: bool = True


@dataclass(frozen=True)
class FactoryCadenceResult:
    tier: FactoryTier
    gates: FactoryGateResult
    put_e2e: PutE2EResult | None = None
    ism_coverage_pct: float | None = None
    factory_complete: bool = False
    skipped: bool = False
    detail: str = ""


def factory_completion_policy_from_rows(
    rows: list[dict[str, Any]],
) -> FactoryCompletionPolicy | None:
    ce = campaign_effective_from_rows(rows)
    if not isinstance(ce, dict):
        return None
    raw = ce.get("completion")
    if not isinstance(raw, dict):
        return None
    tier_raw = raw.get("factory_tier")
    if tier_raw is None:
        return None
    tier = resolve_factory_tier(metadata_tier=str(tier_raw))
    every_n = max(1, int(raw.get("e2e_on_every_n_slices", 5) or 5))
    auto_launch = bool(raw.get("auto_launch_eval", True))
    return FactoryCompletionPolicy(
        factory_tier=tier,
        e2e_on_every_n_slices=every_n,
        auto_launch_eval=auto_launch,
    )


def should_run_factory_cadence(
    slices_completed: int,
    every_n: int,
    *,
    tier: FactoryTier,
) -> bool:
    if tier == "T0":
        return False
    return every_n > 0 and slices_completed > 0 and slices_completed % every_n == 0


def _stage_emitted(rows: list[dict[str, Any]], stage_name: str) -> bool:
    for row in reversed(rows):
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != stage_name:
            continue
        if row.get("event_type") in {
            EventType.STAGE_PASSED.value,
            EventType.STAGE_STARTED.value,
        }:
            return True
    return False


def factory_complete_emitted(rows: list[dict[str, Any]]) -> bool:
    return _stage_emitted(rows, FACTORY_COMPLETE_STAGE)


def launch_eval_completed(rows: list[dict[str, Any]]) -> bool:
    return _stage_emitted(rows, "launch_eval.completed")


def _business_prompt_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata") or {}
        req = meta.get("requirements") or {}
        if isinstance(req, dict):
            return str(req.get("business_prompt") or "").strip()
    return ""


def _emit_factory_stage(
    store: Any,
    run_id: UUID,
    *,
    stage_name: str,
    metadata: dict[str, Any],
) -> None:
    now = datetime.now(timezone.utc)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=metadata,
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=metadata,
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=0),
        ),
    )


def _run_put_e2e_for_run(
    workspace: Path,
    rows: list[dict[str, Any]],
    *,
    tier: FactoryTier,
    repo_root: Path | None,
) -> tuple[bool | None, PutE2EResult | None, Any | None, float | None]:
    from nimbusware_orchestrator.interaction_surface_map import discover_surfaces_static
    from nimbusware_orchestrator.launch_eval_catalog import attach_context_from_run
    from nimbusware_orchestrator.put_runtime import start_put_preview, stop_put_preview

    if tier in {"T0", "T1"}:
        return None, None, None, None

    attach = attach_context_from_run(rows, repo_root)
    flow_id = match_factory_flow_id(
        _business_prompt_from_rows(rows),
        prompt_id=attach.get("prompt_id"),
        repo_root=repo_root,
    )
    if not flow_id:
        skip = PutE2EResult(
            verdict="SKIP",
            flow_id="",
            base_url="",
            detail="no catalog flow match",
        )
        return False, skip, None, None

    port = 19876 + (hash(str(workspace)) % 400)
    preview = start_put_preview(workspace, port, startup_timeout_seconds=12.0)
    put_preview_ok = preview.ok
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    ism = None
    put_e2e: PutE2EResult | None = None
    coverage: float | None = None
    try:
        ism = discover_surfaces_static(
            workspace, preview_base_url=base_url if put_preview_ok else None
        )
        put_e2e = run_put_e2e_flow(
            base_url,
            flow_id,
            repo_root=repo_root,
            workspace=workspace,
            require_playwright=False,
        )
        gates = evaluate_factory_gates(
            tier,
            put_preview_ok=put_preview_ok,
            ism=ism,
            put_e2e=put_e2e,
            repo_root=repo_root,
        )
        coverage_raw = gates.details.get("ism_coverage_pct")
        coverage = float(coverage_raw) if coverage_raw is not None else None
        return put_preview_ok, put_e2e, ism, coverage
    finally:
        stop_put_preview(preview.handle)


def maybe_run_factory_cadence_pass(
    store: Any,
    run_id: UUID,
    rows: list[dict[str, Any]],
    *,
    workspace: Path | None,
    slices_completed: int,
    repo_root: Path | None = None,
    force: bool = False,
) -> FactoryCadenceResult | None:
    policy = factory_completion_policy_from_rows(rows)
    if policy is None:
        return None
    if not force and not should_run_factory_cadence(
        slices_completed,
        policy.e2e_on_every_n_slices,
        tier=policy.factory_tier,
    ):
        return None

    tier = policy.factory_tier
    if policy.auto_launch_eval and not launch_eval_completed(rows):
        from nimbusware_maker.workspace import resolve_run_workspace
        from nimbusware_orchestrator.launch_evaluator import maybe_run_launch_eval_for_campaign

        ws = workspace or resolve_run_workspace(rows)
        maybe_run_launch_eval_for_campaign(store, run_id, rows, workspace=ws)
        rows = store.list_run_events(str(run_id))

    put_preview_ok: bool | None = None
    put_e2e: PutE2EResult | None = None
    ism = None
    coverage: float | None = None
    ws_path = workspace
    if ws_path is None:
        from nimbusware_maker.workspace import resolve_run_workspace

        ws_path = resolve_run_workspace(rows)
    if ws_path.is_dir() and tier in {"T2", "T3"}:
        put_preview_ok, put_e2e, ism, coverage = _run_put_e2e_for_run(
            ws_path,
            rows,
            tier=tier,
            repo_root=repo_root,
        )
        if put_e2e is not None and put_e2e.verdict == "FAIL":
            from nimbusware_orchestrator.backlog_generator import (
                backlog_from_events,
                emit_backlog_revised,
            )

            backlog = backlog_from_events(rows)
            revised = handle_put_e2e_failure(backlog, put_e2e)
            if revised is not None and revised is not backlog:
                emit_backlog_revised(
                    store,
                    run_id,
                    revised,
                    revision_reason="put_e2e_fix_slices",
                )
                rows = store.list_run_events(str(run_id))

    gates = evaluate_factory_gates(
        tier,
        put_preview_ok=put_preview_ok,
        ism=ism,
        put_e2e=put_e2e,
        ism_coverage_pct_value=coverage,
        repo_root=repo_root,
    )
    meta: dict[str, Any] = {
        "factory": {
            "tier": tier,
            "ism_coverage_pct": coverage
            if coverage is not None
            else gates.details.get("ism_coverage_pct"),
            "put_e2e_passed": put_e2e.passed if put_e2e is not None else None,
            "gates_passed": gates.passed,
            "blocking": list(gates.blocking),
        },
    }
    if put_e2e is not None:
        meta["put_e2e"] = put_e2e.to_dict()
    _emit_factory_stage(store, run_id, stage_name=FACTORY_CADENCE_STAGE, metadata=meta)

    factory_complete = (
        gates.passed and tier in {"T2", "T3"} and put_e2e is not None and put_e2e.verdict == "PASS"
    )
    if factory_complete and not factory_complete_emitted(rows):
        complete_meta = dict(meta)
        complete_meta["factory"]["factory_complete"] = True
        _emit_factory_stage(
            store, run_id, stage_name=FACTORY_COMPLETE_STAGE, metadata=complete_meta
        )

    return FactoryCadenceResult(
        tier=tier,
        gates=gates,
        put_e2e=put_e2e,
        ism_coverage_pct=coverage,
        factory_complete=factory_complete,
        detail=f"factory cadence tier={tier} passed={gates.passed}",
    )


def factory_blocks_campaign_pass(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    policy = factory_completion_policy_from_rows(rows)
    if policy is None:
        return ()
    blocking: list[str] = []
    if policy.factory_tier in {"T1", "T2", "T3"} and not launch_eval_completed(rows):
        blocking.append("launch_eval_not_completed")
    if policy.factory_tier in {"T2", "T3"} and not factory_complete_emitted(rows):
        blocking.append("factory_complete_pending")
    return tuple(blocking)
