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
from nimbusware_orchestrator.factory_put_e2e import run_put_e2e_for_factory_run
from nimbusware_orchestrator.put_e2e_runner import PutE2EResult

FACTORY_CADENCE_STAGE = "factory.cadence"
FACTORY_GATE_STAGE = "factory.gate"
FACTORY_COMPLETE_STAGE = "factory.complete"


@dataclass(frozen=True)
class FactoryCompletionPolicy:
    factory_tier: FactoryTier = "T1"
    e2e_on_every_n_slices: int = 5
    auto_launch_eval: bool = True
    raw_factory_tier: str = "T1"
    ui_flow_required: bool = False


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
    raw_str = str(tier_raw)
    tier = resolve_factory_tier(metadata_tier=raw_str)
    from nimbusware_orchestrator.factory_completion import factory_ui_flow_required

    every_n = max(1, int(raw.get("e2e_on_every_n_slices", 5) or 5))
    auto_launch = bool(raw.get("auto_launch_eval", True))
    return FactoryCompletionPolicy(
        factory_tier=tier,
        e2e_on_every_n_slices=every_n,
        auto_launch_eval=auto_launch,
        raw_factory_tier=raw_str,
        ui_flow_required=factory_ui_flow_required(metadata_tier=raw_str),
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
    ism_diff: dict[str, Any] | None = None
    ws_path = workspace
    if ws_path is None:
        from nimbusware_maker.workspace import resolve_run_workspace

        ws_path = resolve_run_workspace(rows)
    ui_passed: bool | None = None
    ui_flow_id: str | None = None
    if ws_path.is_dir() and tier in {"T2", "T3"}:
        put_preview_ok, put_e2e, ism, coverage, ism_diff, ui_passed, ui_flow_id = (
            run_put_e2e_for_factory_run(
                ws_path,
                rows,
                tier=tier,
                repo_root=repo_root,
                store=store,
                run_id=run_id,
                slices_completed=slices_completed,
                ui_flow_required=policy.ui_flow_required if policy else False,
            )
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
            "raw_tier": policy.raw_factory_tier if policy else tier,
            "ism_coverage_pct": coverage
            if coverage is not None
            else gates.details.get("ism_coverage_pct"),
            "put_e2e_passed": put_e2e.passed if put_e2e is not None else None,
            "put_ui_flow_passed": ui_passed,
            "put_ui_flow_id": ui_flow_id,
            "gates_passed": gates.passed,
            "blocking": list(gates.blocking),
        },
    }
    if policy and policy.ui_flow_required and ui_passed is False:
        gates = FactoryGateResult(
            tier=gates.tier,
            passed=False,
            blocking=(*gates.blocking, "put_ui_flow_failed"),
            details=dict(gates.details),
        )
    if put_e2e is not None:
        meta["put_e2e"] = put_e2e.to_dict()
        meta["put"] = {"base_url": put_e2e.base_url}
    if ism_diff is not None:
        meta["ism_diff"] = ism_diff
    gate_meta = {
        "factory": dict(meta["factory"]),
        "gates": {
            "passed": gates.passed,
            "blocking": list(gates.blocking),
            "details": dict(gates.details),
        },
    }
    from nimbusware_orchestrator.ci_bridge import attach_external_ci_metadata

    attach_external_ci_metadata(
        gate_meta,
        run_id=run_id,
        verdict="PASS" if gates.passed else "FAIL",
        stage_name=FACTORY_GATE_STAGE,
    )
    _emit_factory_stage(store, run_id, stage_name=FACTORY_GATE_STAGE, metadata=gate_meta)
    _emit_factory_stage(store, run_id, stage_name=FACTORY_CADENCE_STAGE, metadata=meta)

    ui_ok = not (policy and policy.ui_flow_required) or ui_passed is True
    factory_complete = (
        gates.passed
        and ui_ok
        and tier in {"T2", "T3"}
        and put_e2e is not None
        and put_e2e.verdict == "PASS"
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
