from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from agent_core.mapping import mapping_or_empty
from nimbusware_research.bundle_promotion import list_pending_stitch_catalog_candidates


def _diagnose_fingerprints(rows: list[dict[str, Any]]) -> list[str]:
    fps: list[str] = []
    for row in rows:
        payload = mapping_or_empty(row.get("payload"))
        if str(payload.get("stage_name") or "") != "diagnose.learn":
            continue
        block = mapping_or_empty(mapping_or_empty(row.get("metadata")).get("diagnose_learn"))
        fp = str(block.get("fingerprint") or "").strip()
        if fp:
            fps.append(fp)
    return fps


def stitch_suggestion_for_run(
    rows: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any] | None:
    counts = Counter(_diagnose_fingerprints(rows))
    repeated = [fp for fp, n in counts.items() if n >= 2]
    if not repeated:
        return None
    pending = list_pending_stitch_catalog_candidates(repo_root, limit=5)
    if not pending:
        return None
    candidate = pending[0]
    return {
        "reason": "repeated_failure_fingerprint",
        "fingerprint": repeated[0],
        "repeat_count": counts[repeated[0]],
        "candidate_id": candidate.get("candidate_id"),
        "candidate_run_id": candidate.get("run_id"),
        "summary": str(candidate.get("summary") or "Pending stitch catalog candidate"),
    }
