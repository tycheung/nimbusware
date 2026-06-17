#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_intent_to_patch.json"
_TARGET_MS = 180_000
_MEASURE = _ROOT / "scripts" / "benchmarks" / "measure_intent_to_patch.py"


def _load_snapshot() -> dict[str, object]:
    if not _SNAPSHOT.is_file():
        raise FileNotFoundError(f"missing {_SNAPSHOT}")
    body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("snapshot must be a JSON object")
    return body


def _validate_snapshot(body: dict[str, object]) -> int:
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
    return 0


def _run_live_harness() -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, str(_MEASURE), "--runs", "1"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        print("intent-to-patch gate: live harness failed", file=sys.stderr)
        raise RuntimeError("live harness failed")
    body = json.loads(proc.stdout)
    if not isinstance(body, dict):
        raise ValueError("harness output must be a JSON object")
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-only",
        action="store_true",
        help="Validate committed snapshot only (skip live harness)",
    )
    args = parser.parse_args(argv)

    if not args.snapshot_only:
        try:
            live = _run_live_harness()
        except (RuntimeError, json.JSONDecodeError, OSError) as exc:
            print(f"intent-to-patch gate: {exc}", file=sys.stderr)
            return 1
        median = live.get("median_ms")
        if not isinstance(median, (int, float)) or float(median) > _TARGET_MS:
            print(
                f"intent-to-patch gate: live median {median!r} exceeds {_TARGET_MS}ms",
                file=sys.stderr,
            )
            return 1
        if not live.get("ok"):
            print("intent-to-patch gate: live harness ok=false", file=sys.stderr)
            return 1

    try:
        snap = _load_snapshot()
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"intent-to-patch gate: {exc}", file=sys.stderr)
        return 1

    rc = _validate_snapshot(snap)
    if rc != 0:
        return rc

    median = snap.get("median_ms")
    print(
        f"intent-to-patch CI gate OK (snapshot median={median}ms, target={_TARGET_MS}ms)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
