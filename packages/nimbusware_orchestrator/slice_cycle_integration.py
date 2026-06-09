from __future__ import annotations

import os
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
from nimbusware_orchestrator.dev_env_policy import ui_controller_enabled
from nimbusware_orchestrator.dev_env_regression import run_dev_env_regression
from nimbusware_orchestrator.dev_env_supervisor import (
    DevEnvStartResult,
    start_dev_environment,
)
from nimbusware_orchestrator.diagnose_learn import (
    agent_packet_from_learning,
    diagnose_from_failure,
)
from nimbusware_orchestrator.human_fidelity import run_human_fidelity_suite
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
                    "learning_path": packet.get("path") or packet.get("learning_path"),
                    "excerpt": str(packet.get("excerpt") or "")[:2000],
                },
            },
            payload=StagePassedPayload(stage_name="diagnose.learn", duration_ms=0),
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
    """Launch a campaign from drained `[build]` interjections; return new campaign id."""
    if not cycle.build_from_chat:
        return None
    from nimbusware_orchestrator.campaign import campaign_enabled_for_run

    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if campaign_enabled_for_run(rows):
        from nimbusware_maker.workspace import resolve_run_workspace

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
    ws = Path(workspace_path) if workspace_path else None
    orch.start_campaign(new_run_id, workspace=ws, autonomous=True)
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
    from nimbusware_orchestrator.dev_env_milestones import dev_env_auto_start_enabled

    if not dev_env_auto_start_enabled(rows):
        return None
    return start_dev_environment(store, run_id, workspace, emit_events=True)


def human_fidelity_pre_gate_enabled(rows: list[dict[str, Any]]) -> bool:
    if os.environ.get("NIMBUSWARE_HUMAN_FIDELITY_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
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
    from nimbusware_orchestrator.dev_env_supervisor import active_base_url

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
            payload=StagePassedPayload(stage_name="human_fidelity", duration_ms=0),
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
    from nimbusware_orchestrator.backlog_generator import backlog_from_events, emit_backlog_revised

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
    from nimbusware_orchestrator.dev_env_milestones import dev_env_http_regression_enabled

    if not dev_env_http_regression_enabled(rows):
        return PreGateRegression()

    http = run_dev_env_regression(store, run_id, workspace, emit_events=True)
    http_passed = http.passed
    http_detail = http.detail

    ui_passed: bool | None = None
    ui_detail = ""
    from nimbusware_orchestrator.dev_env_milestones import dev_env_ui_regression_enabled

    if dev_env_ui_regression_enabled(rows):
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
    execute_improvement_track(
        store,
        run_id,
        workspace,
        council.selected,
        repo_root=getattr(store, "repo_root", None),
    )
    return True


def run_research_transplant_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    repo_root: Path | None = None,
) -> bool:
    from agent_core.models.events_payloads import (
        ResearchBriefEmittedPayload,
        ResearchBriefSourcePayload,
    )
    from agent_core.models.events_records import ResearchBriefEmittedEvent
    from nimbusware_env import find_repo_root
    from nimbusware_extensions.phase2 import UniversalCritiqueRouter
    from nimbusware_orchestrator.registry import RoleRegistry
    from nimbusware_research.artifacts import persist_research_brief
    from nimbusware_research.models import ResearchBrief, ResearchBriefSource
    from nimbusware_research.stages_stitch import emit_stitch_stages_stub

    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    root = repo_root or find_repo_root(start=workspace)
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml"
    )
    brief = ResearchBrief(
        brief_kind="code",
        domain_tag="transplant",
        summary="Council-selected research transplant brief (stub).",
        artifact_id=str(uuid4()),
        sources=(
            ResearchBriefSource(
                url="stub://council/research_transplant",
                license="MIT",
                trust_tier="medium",
            ),
        ),
    )
    persist_research_brief(root, brief)
    store.append(
        ResearchBriefEmittedEvent(
            event_type=EventType.RESEARCH_BRIEF_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            actor_role=reg.resolve("code_researcher"),
            payload=ResearchBriefEmittedPayload(
                brief_kind="code",
                domain_tag="transplant",
                summary=brief.summary,
                artifact_id=brief.artifact_id,
                sources=[
                    ResearchBriefSourcePayload(
                        url=s.url,
                        license=s.license,
                        trust_tier=s.trust_tier,
                    )
                    for s in brief.sources
                ],
            ),
        ),
    )
    rows = store.list_run_events(str(rid))
    meta: dict[str, Any] = {}
    for row in rows:
        if row.get("event_type") == EventType.RUN_CREATED.value:
            block = row.get("metadata")
            if isinstance(block, dict):
                meta = block
            break
    stitch_meta = meta.get("stitch") if isinstance(meta.get("stitch"), dict) else {}
    return emit_stitch_stages_stub(
        store,
        reg,
        router,
        run_id=rid,
        repo_root=root,
        run_created_metadata=meta,
        stitch_meta=stitch_meta,
        prior_events=rows,
    )


def execute_improvement_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    track: ImprovementTrack,
    *,
    repo_root: Path | None = None,
) -> None:
    if track in {ImprovementTrack.DISCOVER_FEATURES, ImprovementTrack.SIMPLIFY}:
        explore = run_repo_explore(workspace)
        emit_repo_explore(store, run_id, explore)
        return
    if track == ImprovementTrack.RESEARCH_TRANSPLANT:
        applied = run_research_transplant_track(store, run_id, workspace, repo_root=repo_root)
        rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                metadata={"research_transplant": {"applied": applied}},
                payload=StagePassedPayload(stage_name="research.transplant", duration_ms=0),
            ),
        )
        return
    if track == ImprovementTrack.VARIANT_EXPERIMENT:
        from nimbusware_orchestrator.variant_arena import (
            measure_variant_fitness,
            promote_variant_to_workspace,
        )

        tmp = workspace.resolve() / ".nimbusware" / "variants"
        tmp.mkdir(parents=True, exist_ok=True)
        candidate = create_variant_worktree(workspace, tmp, label="council_variant")
        tests_passed, loc_delta = measure_variant_fitness(candidate, workspace)
        score_variant(candidate, tests_passed=tests_passed, loc_delta=loc_delta)
        arena = promote_winner([candidate])
        promoted = False
        profile = autopilot_profile_from_rows(store.list_run_events(str(run_id)))
        if arena.winner and arena.winner.fitness >= 0.9 and tests_passed and profile.level >= 6:
            promoted = promote_variant_to_workspace(arena.winner, workspace)
        rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
        meta = arena.to_dict()
        if promoted:
            meta["promoted_to_workspace"] = True
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                metadata={"variant_arena": meta},
                payload=StagePassedPayload(stage_name="variant.arena", duration_ms=0),
            ),
        )
        return
    if track == ImprovementTrack.REFACTOR_COHESION:
        from nimbusware_orchestrator.cohesion_graph import build_cohesion_graph

        cohesion = build_cohesion_graph(workspace)
        if cohesion.proposals:
            top = cohesion.proposals[0]
            from agent_core.models.backlog import BacklogSlice
            from nimbusware_orchestrator.backlog_generator import (
                backlog_from_events,
                emit_backlog_revised,
            )

            rows = store.list_run_events(str(run_id))
            backlog = backlog_from_events(rows)
            if backlog is not None and backlog.epics and backlog.epics[0].features:
                fix = BacklogSlice(
                    slice_id=f"cohesion-{uuid4().hex[:8]}",
                    rationale=f"Cohesion refactor: {top.suggestion[:120]}",
                    target_paths=(top.module,),
                )
                feat = backlog.epics[0].features[0]
                epics = list(backlog.epics)
                epics[0] = epics[0].model_copy(
                    update={
                        "features": (
                            feat.model_copy(update={"slices": tuple(list(feat.slices) + [fix])}),
                            *epics[0].features[1:],
                        ),
                    },
                )
                emit_backlog_revised(
                    store,
                    run_id,
                    backlog.model_copy(update={"epics": tuple(epics)}),
                    revision_reason="cohesion_proposal",
                )
        rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                metadata={
                    "cohesion_refactor": {
                        "proposals": len(cohesion.proposals),
                    },
                },
                payload=StagePassedPayload(stage_name="cohesion.refactor", duration_ms=0),
            ),
        )
        return


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
