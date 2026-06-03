from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


def _payload(ev: Mapping[str, Any]) -> dict[str, Any]:
    pl = ev.get("payload")
    return pl if isinstance(pl, dict) else {}


def critic_reliability_summary_from_events(
    events: Sequence[Any],
) -> dict[str, Any]:
    """Run-level critic reliability: FAIL rate, gate blocks, repeat finding heuristic."""
    critic_verdict_count = 0
    critic_fail_count = 0
    gate_block_count = 0
    finding_fingerprints: dict[str, int] = {}

    if not isinstance(events, list):
        events = []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        et = str(ev.get("event_type") or "")
        pl = _payload(ev)
        if et == "critic.verdict.emitted":
            critic_verdict_count += 1
            if str(pl.get("verdict") or "").strip().upper() == "FAIL":
                critic_fail_count += 1
        elif et == "gate.decision.emitted":
            if str(pl.get("verdict") or "").strip().upper() == "FAIL":
                gate_block_count += 1
        elif et == "finding.created":
            stage = str(pl.get("stage_name") or pl.get("producer_stage") or "")
            msg = str(pl.get("message") or pl.get("summary") or "")[:80].strip().lower()
            key = f"{stage}|{msg}"
            if key.strip("|"):
                finding_fingerprints[key] = finding_fingerprints.get(key, 0) + 1

    repeat_paths = sum(1 for n in finding_fingerprints.values() if n > 1)
    fail_rate = critic_fail_count / critic_verdict_count if critic_verdict_count else 0.0
    return {
        "critic_verdict_count": critic_verdict_count,
        "critic_fail_count": critic_fail_count,
        "critic_fail_rate": round(fail_rate, 4),
        "gate_block_count": gate_block_count,
        "repeat_finding_paths": repeat_paths,
    }


def critic_reliability_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not summary:
        return []
    return [
        {"metric": "Critic verdicts", "value": str(summary.get("critic_verdict_count", 0))},
        {"metric": "Critic FAIL count", "value": str(summary.get("critic_fail_count", 0))},
        {
            "metric": "Critic FAIL rate",
            "value": f"{float(summary.get('critic_fail_rate', 0)):.1%}",
        },
        {"metric": "Gate blocks (FAIL)", "value": str(summary.get("gate_block_count", 0))},
        {
            "metric": "Repeat finding paths",
            "value": str(summary.get("repeat_finding_paths", 0)),
        },
    ]


def critic_reliability_caption(summary: Mapping[str, Any] | None) -> str:
    if not summary or int(summary.get("critic_verdict_count") or 0) == 0:
        return "No critic.verdict.emitted events in this run."
    rate = float(summary.get("critic_fail_rate") or 0)
    gates = int(summary.get("gate_block_count") or 0)
    repeat = int(summary.get("repeat_finding_paths") or 0)
    parts = [f"Critic FAIL rate {rate:.1%}", f"{gates} gate block(s)"]
    if repeat:
        parts.append(f"{repeat} repeated finding path(s)")
    return "; ".join(parts) + "."


def critic_reliability_export_json(summary: Mapping[str, Any] | None) -> str:
    return json.dumps(summary or {}, indent=2, ensure_ascii=False)
