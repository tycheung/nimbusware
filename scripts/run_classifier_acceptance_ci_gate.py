#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_classifier_acceptance.json"
_TARGET_RATE = 0.70


def main() -> int:
    if not _SNAPSHOT.is_file():
        print(f"classifier acceptance gate: missing {_SNAPSHOT}", file=sys.stderr)
        return 1
    try:
        body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"classifier acceptance gate: invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(body, dict) or not body.get("ok"):
        print("classifier acceptance gate: snapshot not ok", file=sys.stderr)
        return 1
    rate = body.get("rate")
    if not isinstance(rate, (int, float)):
        print("classifier acceptance gate: rate missing", file=sys.stderr)
        return 1
    if float(rate) < _TARGET_RATE:
        print(
            f"classifier acceptance gate: rate {rate:.0%} below target {_TARGET_RATE:.0%}",
            file=sys.stderr,
        )
        return 1
    print(
        f"classifier acceptance CI gate OK (rate={float(rate):.0%}, target={_TARGET_RATE:.0%})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
