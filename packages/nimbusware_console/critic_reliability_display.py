from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from nimbusware_orchestrator.fleet_critic_reliability import critic_reliability_summary_from_events

__all__ = [
    "critic_reliability_caption",
    "critic_reliability_export_json",
    "critic_reliability_summary_from_events",
    "critic_reliability_table_rows",
    "fleet_critic_reliability_caption",
    "fleet_critic_reliability_table_rows",
]


def _ood_rows(summary: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    ood = int(summary.get("out_of_domain_verdict_count") or 0)
    if ood > 0:
        rows.append(
            {
                "metric": "Out-of-domain verdicts",
                "value": str(ood),
            },
        )
        rows.append(
            {
                "metric": "Out-of-domain rate",
                "value": f"{float(summary.get('out_of_domain_rate', 0)):.1%}",
            },
        )
        rows.append(
            {
                "metric": "In-domain FAIL rate",
                "value": f"{float(summary.get('in_domain_fail_rate', 0)):.1%}",
            },
        )
    return rows


def critic_reliability_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not summary:
        return []
    rows = [
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
    rows.extend(_ood_rows(summary))
    return rows


def critic_reliability_caption(summary: Mapping[str, Any] | None) -> str:
    if not summary or int(summary.get("critic_verdict_count") or 0) == 0:
        return "No critic.verdict.emitted events in this run."
    rate = float(summary.get("critic_fail_rate") or 0)
    gates = int(summary.get("gate_block_count") or 0)
    repeat = int(summary.get("repeat_finding_paths") or 0)
    parts = [f"Critic FAIL rate {rate:.1%}", f"{gates} gate block(s)"]
    ood = int(summary.get("out_of_domain_verdict_count") or 0)
    if ood:
        parts.append(
            f"{ood} out-of-domain verdict(s) ({float(summary.get('out_of_domain_rate', 0)):.1%})",
        )
    if repeat:
        parts.append(f"{repeat} repeated finding path(s)")
    return "; ".join(parts) + "."


def critic_reliability_export_json(summary: Mapping[str, Any] | None) -> str:
    return json.dumps(summary or {}, indent=2, ensure_ascii=False)


def fleet_critic_reliability_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not metrics:
        return []
    rows = [
        {"metric": "Runs scanned", "value": str(metrics.get("runs_scanned", 0))},
        {"metric": "Runs with critics", "value": str(metrics.get("runs_with_critics", 0))},
        {"metric": "Critic verdicts", "value": str(metrics.get("critic_verdict_count", 0))},
        {"metric": "Critic FAIL count", "value": str(metrics.get("critic_fail_count", 0))},
        {
            "metric": "Fleet critic FAIL rate",
            "value": f"{float(metrics.get('critic_fail_rate', 0)):.1%}",
        },
        {"metric": "Gate blocks (FAIL)", "value": str(metrics.get("gate_block_count", 0))},
        {
            "metric": "Repeat finding paths",
            "value": str(metrics.get("repeat_finding_paths", 0)),
        },
    ]
    rows.extend(_ood_rows(metrics))
    return rows


def fleet_critic_reliability_caption(metrics: Mapping[str, Any] | None) -> str:
    if not metrics or int(metrics.get("critic_verdict_count") or 0) == 0:
        return "No critic.verdict.emitted events in scanned runs."
    rate = float(metrics.get("critic_fail_rate") or 0)
    runs = int(metrics.get("runs_with_critics") or 0)
    scanned = int(metrics.get("runs_scanned") or 0)
    parts = [
        f"Fleet critic FAIL rate {rate:.1%} across {runs} run(s) with critics ({scanned} scanned)",
    ]
    ood = int(metrics.get("out_of_domain_verdict_count") or 0)
    if ood:
        parts.append(
            f"{ood} out-of-domain verdict(s) ({float(metrics.get('out_of_domain_rate', 0)):.1%})",
        )
    return "; ".join(parts) + "."
