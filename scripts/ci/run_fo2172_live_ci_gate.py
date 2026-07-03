#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_fo2172_live_journey.json"
_SOAK = _ROOT / "scripts" / "ops" / "run_fo2172_live_journey_soak.py"


def _load_snapshot() -> dict[str, object]:
    if not _SNAPSHOT.is_file():
        raise FileNotFoundError(f"missing {_SNAPSHOT}")
    body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("snapshot must be a JSON object")
    return body


def _run_opt_in_soak() -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, str(_SOAK)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError("opt-in soak harness failed")
    body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("soak output must be a JSON object")
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
            live = _run_opt_in_soak()
        except (RuntimeError, json.JSONDecodeError, OSError) as exc:
            print(f"fo2172 live gate: {exc}", file=sys.stderr)
            return 1
        if not live.get("ok"):
            print("fo2172 live gate: opt-in harness ok=false", file=sys.stderr)
            return 1
        if not live.get("skipped"):
            print(
                "fo2172 live gate: unexpected live run without NIMBUSWARE_FO2172_LIVE",
                file=sys.stderr,
            )
            return 1

    try:
        snap = _load_snapshot()
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"fo2172 live gate: {exc}", file=sys.stderr)
        return 1

    if not snap.get("ok"):
        print("fo2172 live gate: snapshot not ok", file=sys.stderr)
        return 1
    if not snap.get("skipped"):
        print("fo2172 live gate: snapshot must be opt-in skipped in CI", file=sys.stderr)
        return 1

    print("fo2172 live CI gate OK (opt-in snapshot)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
