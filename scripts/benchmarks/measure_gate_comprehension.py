#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "packages") not in sys.path:
    sys.path.insert(0, str(_REPO / "packages"))

_FIXTURE = _REPO / "benchmarks" / "gate_failure_comprehension_fixture.json"
_TARGET = 0.8


def measure_gate_comprehension(*, fixture_path: Path | None = None) -> dict[str, object]:
    from projections.builders.maker_progress import _gate_summary_plain

    path = fixture_path or _FIXTURE
    body = json.loads(path.read_text(encoding="utf-8"))
    scenarios = body.get("scenarios") if isinstance(body, dict) else None
    if not isinstance(scenarios, list):
        raise ValueError("fixture scenarios must be a list")
    target = float(body.get("target_score", _TARGET))
    passed = 0
    rows: list[dict[str, object]] = []
    for row in scenarios:
        if not isinstance(row, dict):
            continue
        latest = row.get("latest_stage")
        blocked = bool(row.get("blocked"))
        summary = _gate_summary_plain(
            blocked=blocked,
            latest_stage=str(latest) if latest else None,
        )
        text = (summary or "").lower()
        expected = [str(p).lower() for p in row.get("expected_phrases") or []]
        ok = all(phrase in text for phrase in expected) if expected else summary is None
        if ok:
            passed += 1
        rows.append(
            {
                "id": row.get("id"),
                "ok": ok,
                "summary": summary,
                "expected_phrases": expected,
            },
        )
    total = len(rows) or 1
    score = round(passed / total, 3)
    return {
        "version": 1,
        "ok": score >= target,
        "target_score": target,
        "fit_score": score,
        "checks_passed": passed,
        "checks_total": total,
        "scenarios": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default="")
    args = parser.parse_args(argv)
    metrics = measure_gate_comprehension()
    if args.json_path:
        out = Path(args.json_path)
        out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0 if metrics.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
