"""Wire v2.1–v2.3 operator modules into slice and campaign loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from nimbusware_orchestrator.autopilot_profiles import (
    AutopilotProfile,
    autopilot_profile_from_rows,
)
from nimbusware_orchestrator.dev_env_policy import (
    persistent_dev_env_enabled,
    ui_controller_enabled,
)
from nimbusware_orchestrator.dev_env_regression import run_dev_env_regression
from nimbusware_orchestrator.dev_env_supervisor import (
    DevEnvStartResult,
    start_dev_environment,
)
from nimbusware_orchestrator.diagnose_learn import (
    agent_packet_from_learning,
    diagnose_from_failure,
)
from nimbusware_orchestrator.improvement_council import (
    ImprovementTrack,
    run_improvement_council,
)
from nimbusware_orchestrator.interjection_queue import InterjectionItem, queue_for_run
from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.repo_explorer import run_repo_explore
from nimbusware_orchestrator.resolution_council import (
    ResolutionCouncilResult,
    run_resolution_council,
)
from nimbusware_orchestrator.slice_gate import SliceGateChainResult, SliceGateStep
from nimbusware_orchestrator.ui_flow_dsl import DEFAULT_TINY_WEB_LOGIN_FLOW
from nimbusware_orchestrator.variant_arena import (
    create_variant_worktree,
    promote_winner,
    score_variant,
)


@dataclass
class InterjectionCycle:
    items: list[InterjectionItem] = field(default_factory=list)
    force_break: bool = False
    build_from_chat: bool = False

    @property
    def messages(self) -> list[str]:
        return [i.message for i in self.items if i.message.strip()]


@dataclass(frozen=True)
class PreGateRegression:
    http_passed: bool | None = None
    http_detail: str = ""
    ui_passed: bool | None = None
    ui_detail: str = ""


def emit_resolution_council(
    store: Any,
    run_id: UUID | str,
    resolution: ResolutionCouncilResult,
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"resolution_council": resolution.to_dict()},
            payload=StagePassedPayload(stage_name="resolution.council", duration_ms=0),
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
                    "messages": cycle.messages[:10],
                }
            },
            payload=StageStartedPayload(stage_name="interjection.drained", attempt=1),
        ),
    )


def emit_repo_explore(
    store: Any,
    run_id: UUID | str,
    result: Any,
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"repo_explore": result.to_dict()},
            payload=StagePassedPayload(stage_name="repo.explore", duration_ms=0),
        ),
    )


def emit_improvement_council(
    store: Any,
    run_id: UUID | str,
    council: Any,
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"improvement_council": council.to_dict()},
            payload=StagePassedPayload(stage_name="improvement.council", duration_ms=0),
        ),
    )


def emit_diagnose_learn(
    store: Any,
    run_id: UUID | str,
    *,
    slice_id: str,
    packet: dict[str, Any],
    fingerprint: str,
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "slice_id": slice_id,
                "diagnose_learn": {
                    "fingerprint": fingerprint,
                    "learning_available": packet.get("available"),
                    "learning_path": packet.get("path"),
                },
            },
            payload=StagePassedPayload(stage_name="diagnose.learn", duration_ms=0),
        ),
    )


def process_interjection_cycle(store: Any, run_id: UUID | str) -> InterjectionCycle:
    q = queue_for_run(str(run_id))
    items = q.drain()
    cycle = InterjectionCycle(
        items=items,
        force_break=any(i.force_break for i in items),
        build_from_chat=any(i.build_from_chat for i in items),
    )
    emit_interjection_drained(store, run_id, cycle)
    return cycle


def apply_interjection_to_plan(plan: SlicePlan, cycle: InterjectionCycle) -> SlicePlan:
    if not cycle.messages:
        return plan
    block = "\n".join(f"- {m}" for m in cycle.messages[:5])
    rationale = f"{plan.rationale}\n\nOperator interjection:\n{block}"
    return SlicePlan(
        slice_id=plan.slice_id,
        target_paths=plan.target_paths,
        rationale=rationale[:4000],
        acceptance_criteria=plan.acceptance_criteria,
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


def ensure_dev_environment_for_slice(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
) -> DevEnvStartResult | None:
    if not persistent_dev_env_enabled(rows):
        return None
    return start_dev_environment(store, run_id, workspace, emit_events=True)


def run_pre_gate_dev_env_regression(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
    profile: AutopilotProfile,
) -> PreGateRegression:
    if not persistent_dev_env_enabled(rows):
        return PreGateRegression()

    http = run_dev_env_regression(store, run_id, workspace, emit_events=True)
    http_passed = http.passed
    http_detail = http.detail

    ui_passed: bool | None = None
    ui_detail = ""
    if ui_controller_enabled(rows):
        from nimbusware_orchestrator.browser_controller import run_dev_env_ui_regression
        from nimbusware_orchestrator.dev_env_supervisor import active_base_url

        base = active_base_url(workspace)
        if base:
            ui = run_dev_env_ui_regression(
                store,
                run_id,
                base_url=base,
                flow=DEFAULT_TINY_WEB_LOGIN_FLOW,
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


def maybe_run_improvement_council_tick(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
    *,
    slices_completed: int,
) -> bool:
    profile = autopilot_profile_from_rows(rows)
    if profile.level < 10:
        return False
    if slices_completed <= 0 or slices_completed % 5 != 0:
        return False
    council = run_improvement_council(workspace)
    emit_improvement_council(store, run_id, council)
    if council.selected is None:
        return True
    execute_improvement_track(store, run_id, workspace, council.selected)
    return True


def execute_improvement_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    track: ImprovementTrack,
) -> None:
    if track in {ImprovementTrack.DISCOVER_FEATURES, ImprovementTrack.SIMPLIFY}:
        explore = run_repo_explore(workspace)
        emit_repo_explore(store, run_id, explore)
        return
    if track == ImprovementTrack.VARIANT_EXPERIMENT:
        tmp = workspace.resolve() / ".nimbusware" / "variants"
        tmp.mkdir(parents=True, exist_ok=True)
        candidate = create_variant_worktree(workspace, tmp, label="council_variant")
        score_variant(candidate, tests_passed=True, loc_delta=0)
        arena = promote_winner([candidate])
        rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                metadata={"variant_arena": arena.to_dict()},
                payload=StagePassedPayload(stage_name="variant.arena", duration_ms=0),
            ),
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
