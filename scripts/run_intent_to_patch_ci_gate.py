#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_intent_to_patch.json"
_TARGET_MS = 180_000


def main() -> int:
    if not _SNAPSHOT.is_file():
        print(f"intent-to-patch gate: missing {_SNAPSHOT}", file=sys.stderr)
        return 1
    try:
        body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"intent-to-patch gate: invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(body, dict):
        print("intent-to-patch gate: snapshot must be a JSON object", file=sys.stderr)
        return 1
    if not body.get("ok"):
        print("intent-to-patch gate: snapshot ok=false", file=sys.stderr)
        return 1
    median = body.get("median_ms")
    if not isinstance(median, (int, float)):
        print("intent-to-patch gate: median_ms missing", file=sys.stderr)
        return 1
    if float(median) > _TARGET_MS:
        print(
            f"intent-to-patch gate: median {median}ms exceeds target {_TARGET_MS}ms",
            file=sys.stderr,
        )
        return 1
    print(
        f"intent-to-patch CI gate OK (median={median}ms, target={_TARGET_MS}ms)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
