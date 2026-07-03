#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "packages") not in sys.path:
    sys.path.insert(0, str(_REPO / "packages"))

from maker.intent_classifier import WorkType, classify_intent

_SCENARIOS: list[tuple[str, WorkType]] = [
    ("fix failing unit test in calculator", WorkType.PATCH),
    ("patch the login regression test", WorkType.PATCH),
    ("failing test in tests/test_calculator.py", WorkType.PATCH),
    ("implement oauth middleware slice", WorkType.SLICE),
    ("micro slice for export feature", WorkType.SLICE),
    ("build todo api backend", WorkType.FACTORY),
    ("factory zero touch crm app", WorkType.FACTORY),
    ("rename this variable quickly", WorkType.QUICK),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default="")
    args = parser.parse_args(argv)
    accepted = 0
    for message, expected in _SCENARIOS:
        result = classify_intent(message, use_llm=False)
        if result.work_type == expected:
            accepted += 1
    total = len(_SCENARIOS)
    rate = accepted / total if total else 0.0
    body = {
        "ok": total > 0,
        "rate": rate,
        "target_rate": 0.70,
        "meets_target": rate >= 0.70,
        "classifier_count": accepted,
        "override_count": total - accepted,
        "sample_size": total,
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture": "scripts/benchmarks/measure_classifier_acceptance.py",
    }
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, indent=2))
    return 0 if body["meets_target"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
