#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_classifier_acceptance.json"
_TARGET_RATE = 0.70
_MEASURE = _ROOT / "scripts" / "benchmarks" / "measure_classifier_acceptance.py"


def _load_snapshot() -> dict[str, object]:
    if not _SNAPSHOT.is_file():
        raise FileNotFoundError(f"missing {_SNAPSHOT}")
    body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("snapshot must be a JSON object")
    return body


def _validate_snapshot(body: dict[str, object]) -> int:
    if not body.get("ok"):
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
    return 0


def _run_live_harness() -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, str(_MEASURE)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        print("classifier acceptance gate: live harness failed", file=sys.stderr)
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
            print(f"classifier acceptance gate: {exc}", file=sys.stderr)
            return 1
        rate = live.get("rate")
        if not isinstance(rate, (int, float)) or float(rate) < _TARGET_RATE:
            print(
                f"classifier acceptance gate: live rate {rate!r} below {_TARGET_RATE:.0%}",
                file=sys.stderr,
            )
            return 1
        if not live.get("ok"):
            print("classifier acceptance gate: live harness ok=false", file=sys.stderr)
            return 1

    try:
        snap = _load_snapshot()
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"classifier acceptance gate: {exc}", file=sys.stderr)
        return 1

    rc = _validate_snapshot(snap)
    if rc != 0:
        return rc

    rate = snap.get("rate")
    print(
        f"classifier acceptance CI gate OK (snapshot rate={float(rate):.0%}, "
        f"target={_TARGET_RATE:.0%})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
