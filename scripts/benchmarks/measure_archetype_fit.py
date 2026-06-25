"""Measure consumer archetype fit metrics from recent run timelines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from nimbusware_env import find_repo_root


def _archetype_from_metadata(meta: dict) -> str:
    raw = str(meta.get("consumer_archetype") or "").strip()
    if raw:
        return raw
    wf = str(meta.get("workflow_profile") or meta.get("work_type") or "").strip()
    if wf == "safe_coding":
        return "safe_coding"
    return "engineer"


def measure_archetype_fit(
    *,
    repo_root: Path | None = None,
    run_limit: int = 200,
) -> dict:
    root = repo_root or find_repo_root()
    from nimbusware_store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    counts: dict[str, int] = {"safe_coding": 0, "engineer": 0, "other": 0}
    rows = store.list_all_event_rows() if hasattr(store, "list_all_event_rows") else []
    seen: set[str] = set()
    for row in reversed(rows[-run_limit:]):
        if row.get("event_type") != "run.created":
            continue
        run_id = str(row.get("run_id") or "")
        if not run_id or run_id in seen:
            continue
        seen.add(run_id)
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        arch = _archetype_from_metadata(meta)
        if arch in counts:
            counts[arch] += 1
        else:
            counts["other"] += 1
    total = sum(counts.values()) or 1
    return {
        "version": 1,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "archetypes": {
            "safe_coding": {
                "fit_score": round(counts["safe_coding"] / total, 3),
                "run_count": counts["safe_coding"],
            },
            "engineer": {
                "fit_score": round(counts["engineer"] / total, 3),
                "run_count": counts["engineer"],
            },
        },
        "other_run_count": counts["other"],
        "repo_root": str(root),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure archetype fit metrics")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("scripts/benchmarks/latest_archetype_metrics.json"),
    )
    args = parser.parse_args()
    metrics = measure_archetype_fit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
