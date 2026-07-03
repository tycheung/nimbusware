from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from orchestrator.dev_env.policy import (
    human_fidelity_profile_enabled,
    ui_controller_enabled,
)
from orchestrator.dev_env.regression import run_dev_env_regression
from orchestrator.dev_env.supervisor import (
    DevEnvStartResult,
    start_dev_environment,
)
from orchestrator.factory.human_fidelity import run_human_fidelity_suite
from orchestrator.improvement.diagnose_learn import (
    agent_packet_from_learning,
    diagnose_from_failure,
)
from orchestrator.improvement.resolution_council import (
    ResolutionCouncilResult,
    run_resolution_council,
)
from orchestrator.launch.launch_flow_resolver import resolve_launch_flows
from orchestrator.profiles.autopilot_profiles import (
    AutopilotProfile,
    autopilot_profile_from_rows,
)
from orchestrator.repo_intel.explorer import run_repo_explore
from orchestrator.slice.cycle_emits import (
    emit_diagnose_learn,
    emit_repo_explore,
    emit_resolution_council,
)
from orchestrator.slice.cycle_improvement import (
    execute_improvement_track,
    maybe_run_improvement_council_tick,
    run_research_transplant_track,
)
from orchestrator.slice.gate import SliceGateChainResult, SliceGateStep
from orchestrator.slice.micro_slice import SlicePlan
from orchestrator.ui_flow_dsl import DEFAULT_TINY_WEB_LOGIN_FLOW


@dataclass(frozen=True)
class PreGateRegression:
    http_passed: bool | None = None
    http_detail: str = ""
    ui_passed: bool | None = None
    ui_detail: str = ""


def ensure_dev_environment_for_slice(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
) -> DevEnvStartResult | None:
    from orchestrator.dev_env.milestones import dev_env_auto_start_enabled

    if not dev_env_auto_start_enabled(rows):
        return None
    return start_dev_environment(store, run_id, workspace, emit_events=True)


def human_fidelity_pre_gate_enabled(rows: list[dict[str, Any]]) -> bool:
    if human_fidelity_profile_enabled(rows):
        return True
    profile = autopilot_profile_from_rows(rows)
    if profile.level <= 5:
        return ui_controller_enabled(rows)
    return False


def maybe_run_human_fidelity_pre_gate(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
) -> tuple[bool | None, str]:
    if not human_fidelity_pre_gate_enabled(rows):
        return None, ""
    from orchestrator.dev_env.supervisor import active_base_url

    base = active_base_url(workspace)
    if not base:
        return None, "human_fidelity skipped (no dev env base url)"
    result = run_human_fidelity_suite(base)
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"human_fidelity": {"passed": result.passed, "detail": result.detail}},
            payload=StagePassedPayload(stage_name="dev_env.human_fidelity", duration_ms=0),
        ),
    )
    return result.passed, result.detail


def maybe_run_repo_explore_slice_stage(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    slice_index: int,
) -> bool:
    if slice_index != 1 and slice_index % 3 != 0:
        return False
    explore = run_repo_explore(workspace)
    emit_repo_explore(store, run_id, explore)
    if not explore.findings:
        return True
    from agent_core.models.backlog import BacklogSlice
    from orchestrator.campaign.generator import backlog_from_events, emit_backlog_revised

    rows = store.list_run_events(str(run_id))
    backlog = backlog_from_events(rows)
    if backlog is None:
        return True
    finding = explore.findings[0]
    target = (finding.path,) if finding.path else ("packages/",)
    fix = BacklogSlice(
        slice_id=f"explore-{slice_index}",
        rationale=f"Repo explore: {finding.message}",
        target_paths=target,
    )
    epics = list(backlog.epics)
    if epics and epics[0].features:
        feat = epics[0].features[0]
        new_slices = tuple(list(feat.slices) + [fix])
        epics[0] = epics[0].model_copy(
            update={
                "features": (feat.model_copy(update={"slices": new_slices}), *epics[0].features[1:])
            },
        )
        from agent_core.models.backlog import sync_backlog_metadata

        revised = sync_backlog_metadata(backlog.model_copy(update={"epics": tuple(epics)}))
        emit_backlog_revised(store, run_id, revised, revision_reason="repo_explore_finding")
    return True


def run_pre_gate_dev_env_regression(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
    profile: AutopilotProfile,
) -> PreGateRegression:
    from orchestrator.dev_env.milestones import dev_env_http_regression_enabled

    if not dev_env_http_regression_enabled(rows):
        return PreGateRegression()

    http = run_dev_env_regression(store, run_id, workspace, emit_events=True)
    http_passed = http.passed
    http_detail = http.detail

    ui_passed: bool | None = None
    ui_detail = ""
    from orchestrator.dev_env.milestones import dev_env_ui_regression_enabled

    if dev_env_ui_regression_enabled(rows):
        from orchestrator.browser_controller import run_dev_env_ui_regression
        from orchestrator.dev_env.supervisor import frontend_base_url

        base = frontend_base_url(workspace)
        if base:
            resolved = resolve_launch_flows(rows, workspace)
            flow = resolved.ui_flow or DEFAULT_TINY_WEB_LOGIN_FLOW
            ui = run_dev_env_ui_regression(
                store,
                run_id,
                base_url=base,
                flow=flow,
                workspace=workspace,
                emit_events=True,
            )
            ui_passed = ui.passed
            ui_detail = ui.detail

    return PreGateRegression(
        http_passed=http_passed,
        http_detail=http_detail,
        ui_passed=ui_passed,
        ui_detail=ui_detail,
    )


def merge_pre_gate_into_verify(
    verify_ok: bool,
    verify_log: str,
    pre: PreGateRegression,
) -> tuple[bool, str]:
    ok = verify_ok
    sections = [verify_log] if verify_log else []
    if pre.http_passed is False:
        ok = False
        sections.append(f"[dev_env.regression] {pre.http_detail}")
    if pre.ui_passed is False:
        ok = False
        sections.append(f"[dev_env.ui_regression] {pre.ui_detail}")
    return ok, "\n".join(s for s in sections if s)


def handle_gate_failure_learning(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    plan: SlicePlan,
    gate: SliceGateChainResult,
) -> dict[str, Any]:
    failing = [s for s in gate.steps if s.verdict == "FAIL"]
    if not failing:
        return {}
    error_text = "; ".join(f"{s.name}: {s.detail}" for s in failing[:5])
    result = diagnose_from_failure(workspace, error_text=error_text)
    packet = agent_packet_from_learning(workspace, result.fingerprint)
    emit_diagnose_learn(
        store,
        run_id,
        slice_id=plan.slice_id,
        packet=packet,
        fingerprint=result.fingerprint,
    )
    return packet


def apply_operator_pause(
    gate: SliceGateChainResult,
    profile: AutopilotProfile,
    *,
    dev_env_failed: bool = False,
    ui_regression_failed: bool = False,
) -> SliceGateChainResult:
    if gate.passed:
        return gate
    checkpoint: str | None = None
    if profile.should_stop("stop_on_gate_fail"):
        checkpoint = "stop_on_gate_fail"
    elif dev_env_failed and profile.should_stop("stop_on_dev_env_regression_fail"):
        checkpoint = "stop_on_dev_env_regression_fail"
    elif ui_regression_failed and profile.should_stop("stop_on_ui_regression_fail"):
        checkpoint = "stop_on_ui_regression_fail"
    if checkpoint is None:
        return gate
    return SliceGateChainResult(
        slice_id=gate.slice_id,
        passed=False,
        steps=gate.steps + (SliceGateStep("autopilot.pause", "FAIL", checkpoint),),
        status="paused_for_operator",
    )


def resolution_for_gate(
    store: Any,
    run_id: UUID | str,
    rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> ResolutionCouncilResult:
    profile = autopilot_profile_from_rows(rows)
    resolution = run_resolution_council(findings=findings, autopilot_level=profile.level)
    emit_resolution_council(store, run_id, resolution)
    return resolution


__all__ = [
    "PreGateRegression",
    "apply_operator_pause",
    "ensure_dev_environment_for_slice",
    "execute_improvement_track",
    "handle_gate_failure_learning",
    "maybe_run_human_fidelity_pre_gate",
    "maybe_run_improvement_council_tick",
    "maybe_run_repo_explore_slice_stage",
    "merge_pre_gate_into_verify",
    "resolution_for_gate",
    "run_pre_gate_dev_env_regression",
    "run_research_transplant_track",
]
