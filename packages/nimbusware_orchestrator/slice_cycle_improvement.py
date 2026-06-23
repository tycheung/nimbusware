from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from nimbusware_orchestrator.autopilot_profiles import autopilot_profile_from_rows
from nimbusware_orchestrator.improvement_council import ImprovementTrack, run_improvement_council
from nimbusware_orchestrator.repo_explorer import run_repo_explore
from nimbusware_orchestrator.slice_cycle_emits import emit_improvement_council, emit_repo_explore


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


RESEARCH_TRANSPLANT_SKIP_STAGE = "research.transplant.skipped"


def _emit_research_transplant_skipped(
    store: Any,
    run_id: UUID,
    *,
    reason: str,
) -> bool:
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"research_transplant": {"skipped": True, "reason": reason}},
            payload=StagePassedPayload(stage_name=RESEARCH_TRANSPLANT_SKIP_STAGE, duration_ms=0),
        ),
    )
    return False


def run_research_transplant_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    repo_root: Path | None = None,
) -> bool:
    import json

    from agent_core.models.events_payloads import (
        ResearchBriefEmittedPayload,
        ResearchBriefSourcePayload,
    )
    from agent_core.models.events_records import ResearchBriefEmittedEvent
    from nimbusware_env import find_repo_root
    from nimbusware_extensions.phase2 import UniversalCritiqueRouter
    from nimbusware_orchestrator.registry import RoleRegistry
    from nimbusware_research.artifacts import persist_research_brief
    from nimbusware_research.bundle_promotion import list_pending_stitch_catalog_candidates
    from nimbusware_research.models import ResearchBrief, ResearchBriefSource
    from nimbusware_research.pattern_index import pattern_index_path
    from nimbusware_research.stages_stitch import (
        emit_stitch_stages_for_manifest,
        manifest_from_catalog_candidate,
    )
    from nimbusware_research.stitch_models import TransplantManifest

    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    catalog_root = (
        workspace.resolve()
        if (workspace / ".nimbusware" / "research").is_dir()
        else (repo_root or find_repo_root(start=workspace)).resolve()
    )
    config_root = (repo_root or find_repo_root(start=workspace)).resolve()
    pending = list_pending_stitch_catalog_candidates(catalog_root, limit=1)
    candidate = pending[0] if pending else None
    manifest: TransplantManifest | None = None
    brief_url: str | None = None
    brief_summary: str | None = None
    write_catalog_on_apply = True
    wiring_summary: str | None = None
    if candidate is not None:
        manifest = manifest_from_catalog_candidate(catalog_root, candidate)
        run_key = str(candidate.get("run_id") or "unknown")
        candidate_id = str(candidate.get("candidate_id") or "unknown")
        brief_url = f"catalog://{run_key}/{candidate_id}"
        brief_summary = str(
            candidate.get("title") or candidate.get("summary") or "Stitch catalog transplant",
        )
        write_catalog_on_apply = False
        wiring_summary = (
            f"Integrate pending stitch catalog candidate {candidate_id} "
            f"(manifest {manifest.manifest_id})."
        )
    else:
        from nimbusware_projections.builders.run_research import run_research_briefs_from_events

        event_rows = store.list_run_events(str(rid))
        approved = [
            b
            for b in (run_research_briefs_from_events(event_rows).get("briefs") or [])
            if b.get("status") == "approved"
        ]
        if approved:
            entry = approved[0]
            brief_summary = str(entry.get("summary") or brief_summary)
            sources = entry.get("sources") or []
            if sources and isinstance(sources[0], dict):
                url = sources[0].get("url")
                if url:
                    brief_url = str(url)
            wiring_summary = wiring_summary or "Approved research brief from run events."
        pattern_path = pattern_index_path(catalog_root)
        if not approved and pattern_path.is_file():
            try:
                loaded = json.loads(pattern_path.read_text(encoding="utf-8"))
                entries = (
                    [e for e in loaded if isinstance(e, dict)] if isinstance(loaded, list) else []
                )
            except (OSError, json.JSONDecodeError):
                entries = []
            if entries:
                entry = entries[-1]
                brief_url = str(entry.get("repo_url") or brief_url)
                pattern_id = str(entry.get("pattern_id") or "pattern")
                brief_summary = f"Research transplant from indexed pattern {pattern_id}."
                paths_raw = entry.get("paths") or []
                paths = (
                    tuple(str(p) for p in paths_raw if p is not None)
                    if isinstance(paths_raw, list)
                    else ()
                )
                license_name = str(entry.get("license") or "MIT")
                manifest = TransplantManifest(
                    manifest_id=f"pattern-{pattern_id[:24]}",
                    source_kind="oss",
                    source_tree_hash=f"pattern:{pattern_id[:16]}",
                    file_paths=paths,
                    license_paths=("LICENSE",),
                    required_env_vars=(),
                )
                wiring_summary = f"Transplant paths from pattern index ({license_name})."
    if brief_url is None or not str(brief_url).strip():
        return _emit_research_transplant_skipped(store, rid, reason="no_transplant_source")
    if manifest is None:
        return _emit_research_transplant_skipped(store, rid, reason="no_transplant_manifest")
    reg = RoleRegistry.from_yaml(config_root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        config_root / "configs" / "personas" / "critique_pairings.yaml",
    )
    brief = ResearchBrief(
        brief_kind="code",
        domain_tag="transplant",
        summary=brief_summary,
        artifact_id=str(uuid4()),
        sources=(
            ResearchBriefSource(
                url=brief_url,
                license="MIT",
                trust_tier="medium",
            ),
        ),
    )
    persist_research_brief(catalog_root, brief)
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
    stitch_meta = mapping_or_empty(meta.get("stitch"))
    return emit_stitch_stages_for_manifest(
        store,
        reg,
        router,
        run_id=rid,
        repo_root=catalog_root,
        run_created_metadata=meta,
        stitch_meta=stitch_meta,
        prior_events=rows,
        manifest=manifest,
        wiring_delta_summary=wiring_summary,
        write_catalog_on_apply=write_catalog_on_apply,
    )


def execute_improvement_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    track: ImprovementTrack,
    *,
    repo_root: Path | None = None,
) -> None:
    if track == ImprovementTrack.SIMPLIFY:
        from nimbusware_orchestrator.simplification_rubric_critique import (
            emit_simplification_rubric_stage,
        )

        emit_simplification_rubric_stage(store, run_id, workspace)
    if track in {ImprovementTrack.DISCOVER_FEATURES, ImprovementTrack.SIMPLIFY}:
        explore = run_repo_explore(workspace)
        emit_repo_explore(store, run_id, explore)
        from nimbusware_orchestrator.improvement_council_backlog import queue_council_backlog_slice

        if track == ImprovementTrack.SIMPLIFY:
            queue_council_backlog_slice(store, run_id, workspace, track)
        return
    if track == ImprovementTrack.IMPLEMENT_PLANNED:
        from nimbusware_orchestrator.improvement_council_backlog import queue_council_backlog_slice

        queue_council_backlog_slice(store, run_id, workspace, track)
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
            promote_variant_to_workspace,
            run_variant_arena,
            select_promotion_candidate,
        )

        tmp = workspace.resolve() / ".nimbusware" / "variants"
        profile = autopilot_profile_from_rows(store.list_run_events(str(run_id)))
        max_candidates = 4 if profile.level >= 6 else 1
        arena = run_variant_arena(workspace, tmp, max_candidates=max_candidates)
        promotion, crossover_merged, crossover_paths = select_promotion_candidate(
            workspace.resolve(),
            arena.candidates,
            tmp,
        )
        winner = promotion or arena.winner
        tests_passed = winner is not None and winner.fitness >= 0.9
        promoted = False
        if winner and tests_passed and profile.level >= 6:
            promoted = promote_variant_to_workspace(winner, workspace)
        rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
        meta = arena.to_dict()
        if winner:
            meta["winner"] = {
                "variant_id": winner.variant_id,
                "label": winner.label,
                "fitness": winner.fitness,
            }
        if crossover_merged:
            meta["crossover_merged"] = True
            meta["crossover_paths"] = crossover_paths
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
            from nimbusware_orchestrator.simplification_gate import delete_with_tests_allowed

            allowed, gate_detail = delete_with_tests_allowed(workspace, (top.module,))
            if not allowed:
                rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
                store.append(
                    StagePassedEvent(
                        event_type=EventType.STAGE_PASSED,
                        event_id=uuid4(),
                        run_id=rid,
                        occurred_at=datetime.now(timezone.utc),
                        metadata={"simplification_gate": {"allowed": False, "detail": gate_detail}},
                        payload=StagePassedPayload(
                            stage_name="simplification.delete_with_tests.blocked",
                            duration_ms=0,
                        ),
                    ),
                )
                return
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


