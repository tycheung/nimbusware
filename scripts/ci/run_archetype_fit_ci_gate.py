#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT = _ROOT / "benchmarks" / "latest_archetype_metrics.json"
_TARGET_SCORE = 0.85
_MEASURE = _ROOT / "scripts" / "benchmarks" / "measure_archetype_fit.py"


def _load_snapshot() -> dict[str, object]:
    if not _SNAPSHOT.is_file():
        raise FileNotFoundError(f"missing {_SNAPSHOT}")
    body = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("snapshot must be a JSON object")
    return body


def _archetype_score(body: dict[str, object], name: str) -> float | None:
    archetypes = body.get("archetypes")
    if not isinstance(archetypes, dict):
        return None
    row = archetypes.get(name)
    if not isinstance(row, dict):
        return None
    score = row.get("fit_score")
    return float(score) if isinstance(score, (int, float)) else None


def _validate_snapshot(body: dict[str, object]) -> int:
    if not body.get("ok"):
        print("archetype fit gate: snapshot not ok", file=sys.stderr)
        return 1
    for name in ("safe_coding", "engineer"):
        score = _archetype_score(body, name)
        if score is None:
            print(f"archetype fit gate: {name} fit_score missing", file=sys.stderr)
            return 1
        if score < _TARGET_SCORE:
            print(
                f"archetype fit gate: {name} fit_score {score:.0%} below {_TARGET_SCORE:.0%}",
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
            print(f"archetype fit gate: {exc}", file=sys.stderr)
            return 1
        if not live.get("ok"):
            print("archetype fit gate: live harness ok=false", file=sys.stderr)
            return 1
        for name in ("safe_coding", "engineer"):
            score = _archetype_score(live, name)
            if score is None or score < _TARGET_SCORE:
                print(
                    f"archetype fit gate: live {name} score {score!r} below {_TARGET_SCORE:.0%}",
                    file=sys.stderr,
                )
                return 1

    try:
        snap = _load_snapshot()
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"archetype fit gate: {exc}", file=sys.stderr)
        return 1

    rc = _validate_snapshot(snap)
    if rc != 0:
        return rc

    safe = _archetype_score(snap, "safe_coding")
    engineer = _archetype_score(snap, "engineer")
    print(
        f"archetype fit CI gate OK (safe_coding={safe:.0%}, engineer={engineer:.0%}, "
        f"target={_TARGET_SCORE:.0%})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
