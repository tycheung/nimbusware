#!/usr/bin/env python3
"""Run all streams in a standards profile (local CI parity for GHA stream matrix).

Set NIMBUSWARE_CI_STREAMS_SKIP_TEST=1 to omit the ``test`` stream (pytest.unit).
Used by ci_check.ps1 / ci_check.sh so unit pytest runs once with coverage afterward.
GitHub Actions stream jobs are unaffected (each job uses run_stream.py directly).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from standards.registry import profile_stream_ids
from standards.runner import aggregate_passed, run_streams


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a standards profile (multiple streams).")
    parser.add_argument(
        "--profile",
        default="nimbusware-core",
        help="Profile id from configs/standards/streams.yaml",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON results")
    parser.add_argument(
        "--out-dir",
        default="",
        help="Write per-stream JSON files to this directory (for CI artifact aggregation)",
    )
    args = parser.parse_args()
    stream_ids = profile_stream_ids(args.profile)
    skip_test = os.environ.get("NIMBUSWARE_CI_STREAMS_SKIP_TEST", "").strip().lower()
    if skip_test in ("1", "true", "yes"):
        stream_ids = [sid for sid in stream_ids if sid != "test"]
    results = run_streams(stream_ids)
    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for stream_id, result in results.items():
            (out_dir / f"{stream_id}.json").write_text(
                json.dumps(result.to_dict(), indent=2),
                encoding="utf-8",
            )
    if args.json:
        print(json.dumps({k: v.to_dict() for k, v in results.items()}, indent=2))
    else:
        for stream_id, result in results.items():
            print(f"stream {stream_id}: {'ok' if result.passed else 'FAIL'}")
            for check in result.checks:
                status = "ok" if check.passed else "FAIL"
                print(f"  {check.check_id}: {status}")
    ok = aggregate_passed(results)
    if not ok:
        print(f"standards profile {args.profile!r} failed", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
