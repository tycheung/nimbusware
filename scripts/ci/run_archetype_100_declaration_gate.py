#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_STREAK = _ROOT / "benchmarks" / "archetype_fit_streak.json"
_DECLARATION = _ROOT / "benchmarks" / "archetype_fit_100_declaration.json"
_WEEKS_REQUIRED = 4
_TARGET = 0.95


def _load_streak() -> dict[str, object]:
    if not _STREAK.is_file():
        return {"version": 1, "weeks": []}
    body = json.loads(_STREAK.read_text(encoding="utf-8"))
    return body if isinstance(body, dict) else {"version": 1, "weeks": []}


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def _record_week(metrics: dict[str, object]) -> dict[str, object]:
    streak = _load_streak()
    weeks = list(streak.get("weeks") or [])
    key = _week_key()
    entry = {
        "week": key,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(metrics.get("ok")),
        "archetypes": metrics.get("archetypes"),
    }
    weeks = [w for w in weeks if not (isinstance(w, dict) and w.get("week") == key)]
    weeks.append(entry)
    weeks = weeks[-12:]
    out = {"version": 1, "weeks": weeks, "target_score": _TARGET}
    _STREAK.parent.mkdir(parents=True, exist_ok=True)
    _STREAK.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def _consecutive_ok_weeks(weeks: list[object]) -> int:
    streak = 0
    for row in reversed(weeks):
        if not isinstance(row, dict) or not row.get("ok"):
            break
        streak += 1
    return streak


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "benchmarks" / "measure_archetype_fit.py")],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    metrics = json.loads(proc.stdout)
    streak = _record_week(metrics)
    weeks = streak.get("weeks") or []
    consecutive = _consecutive_ok_weeks(weeks)
    gate_proc = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "benchmarks" / "measure_gate_comprehension.py")],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    gate_ok = gate_proc.returncode == 0
    declared = consecutive >= _WEEKS_REQUIRED and bool(metrics.get("ok")) and gate_ok
    declaration = {
        "version": 1,
        "declared": declared,
        "consecutive_ok_weeks": consecutive,
        "weeks_required": _WEEKS_REQUIRED,
        "archetype_metrics_ok": bool(metrics.get("ok")),
        "gate_comprehension_ok": gate_ok,
        "declared_at": datetime.now(timezone.utc).isoformat() if declared else None,
    }
    _DECLARATION.write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
    if not declared:
        print(
            f"archetype 100% declaration: not met "
            f"(consecutive_weeks={consecutive}/{_WEEKS_REQUIRED}, "
            f"metrics_ok={metrics.get('ok')}, gate_comprehension_ok={gate_ok})",
            file=sys.stderr,
        )
        return 1
    print("archetype 100% declaration gate OK (fo2044)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
