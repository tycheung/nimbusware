#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

from standards.runner import aggregate_passed, run_profile


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a standards profile (multiple streams).")
    parser.add_argument(
        "--profile",
        default="nimbusware-core",
        help="Profile id from configs/standards/streams.yaml",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON results")
    args = parser.parse_args()
    results = run_profile(args.profile)
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
