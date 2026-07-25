from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models.backlog import BacklogSlice
from orchestrator.campaign.generator import backlog_from_events, emit_backlog_revised
from orchestrator.improvement.improvement_council import ImprovementTrack


def queue_council_backlog_slice(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    track: ImprovementTrack,
    *,
    rationale_override: str | None = None,
    target_paths_override: tuple[str, ...] | None = None,
) -> bool:
    rows = store.list_run_events(str(run_id))
    backlog = backlog_from_events(rows)
    if backlog is None or not backlog.epics or not backlog.epics[0].features:
        return False

    target_paths: tuple[str, ...] = ("packages/",)
    rationale = rationale_override or f"Council track: {track.value}"

    if target_paths_override is not None:
        target_paths = target_paths_override
    elif track == ImprovementTrack.SIMPLIFY:
        from orchestrator.repo_intel.store import load_or_build_code_intel

        intel = load_or_build_code_intel(workspace, workspace)
        orphans_raw = intel.get("orphans")
        orphans: list[str] = []
        if isinstance(orphans_raw, dict):
            raw_list = orphans_raw.get("orphans")
            if isinstance(raw_list, list):
                orphans = [str(x) for x in raw_list if isinstance(x, str) and x.strip()]
        if orphans:
            target_paths = (orphans[0],)
            rationale = f"Council simplify: wire or remove orphan `{orphans[0]}`"
        else:
            return False
    elif track == ImprovementTrack.IMPLEMENT_PLANNED:
        from orchestrator.improvement.feature_gap_matrix import build_feature_gap_matrix

        gap = build_feature_gap_matrix(workspace)
        if gap.gaps:
            rationale = f"Council implement planned: {gap.gaps[0]}"
        else:
            rationale = "Council implement planned: continue backlog features"
    elif track == ImprovementTrack.IMPROVE_COVERAGE:
        target_paths = ("tests/",)
        rationale = "Council improve coverage: add scoped tests for recent modules"
    elif track == ImprovementTrack.DISCOVER_FEATURES:
        rationale = "Council discover features: research product/market gaps and enqueue epic"
        target_paths = (".nimbusware/campaign/",)
    elif track == ImprovementTrack.SECURITY_HARDEN:
        rationale = "Council security harden: remediate open security findings"
        target_paths = ("packages/", "src/")
    elif track == ImprovementTrack.PERFORMANCE_TUNE:
        rationale = "Council performance tune: address hot-path / perf critique findings"
        target_paths = ("packages/", "src/")
    elif track == ImprovementTrack.DOCUMENT_CONTRACTS:
        rationale = "Council document contracts: align API↔web / ISM surfaces"
        target_paths = (".nimbusware/ism/",)
    elif track == ImprovementTrack.ARCHITECTURE_REVISE:
        rationale = "Council architecture revise: structural follow-up slice"
    else:
        return False

    fix = BacklogSlice(
        slice_id=f"council-{track.value}-{uuid4().hex[:8]}",
        rationale=rationale,
        target_paths=target_paths,
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
        revision_reason=f"council_{track.value}",
    )
    return True
