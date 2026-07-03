from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projections.builders.maker_progress import _slice_gate_rows


def _gate_pass_rate_for_run_rows(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gates = _slice_gate_rows(run_rows)
    if not gates:
        return {"pass_count": 0, "fail_count": 0, "total": 0, "rate": None}
    pass_n = sum(1 for g in gates.values() if g.get("verdict") == "PASS")
    fail_n = sum(1 for g in gates.values() if g.get("verdict") == "FAIL")
    total = len(gates)
    rate = pass_n / total if total else None
    return {"pass_count": pass_n, "fail_count": fail_n, "total": total, "rate": rate}


def policy_compare_outcome_path(repo_root: Path) -> Path:
    return repo_root / "var" / "policy_compare_latest.json"


def build_policy_compare_outcome(
    store: Any,
    *,
    run_a: str,
    run_b: str,
    policy_identical: bool,
    changed_count: int,
) -> dict[str, Any]:
    rows_a = store.list_run_events(run_a)
    rows_b = store.list_run_events(run_b)
    gate_a = _gate_pass_rate_for_run_rows(rows_a)
    gate_b = _gate_pass_rate_for_run_rows(rows_b)
    rate_a = gate_a.get("rate")
    rate_b = gate_b.get("rate")
    delta = None
    if isinstance(rate_a, (int, float)) and isinstance(rate_b, (int, float)):
        delta = float(rate_b) - float(rate_a)
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_a": run_a,
        "run_b": run_b,
        "policy_identical": policy_identical,
        "policy_changed_count": changed_count,
        "run_a_gate": gate_a,
        "run_b_gate": gate_b,
        "gate_pass_rate_delta": delta,
    }


def save_policy_compare_outcome(repo_root: Path, outcome: dict[str, Any]) -> Path:
    path = policy_compare_outcome_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    return path


def load_policy_compare_outcome(repo_root: Path | None) -> dict[str, Any] | None:
    if repo_root is None:
        return None
    path = policy_compare_outcome_path(repo_root)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None
