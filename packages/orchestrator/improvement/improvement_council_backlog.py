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
) -> bool:
    rows = store.list_run_events(str(run_id))
    backlog = backlog_from_events(rows)
    if backlog is None or not backlog.epics or not backlog.epics[0].features:
        return False

    target_paths: tuple[str, ...] = ("packages/",)
    rationale = f"Council track: {track.value}"

    if track == ImprovementTrack.SIMPLIFY:
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
