#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

from standards.runner import run_stream


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single standards CI stream.")
    parser.add_argument("--stream", required=True, help="Stream id from configs/standards/streams.yaml")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args()
    result = run_stream(args.stream)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"stream {result.stream_id}: {'ok' if result.passed else 'FAIL'}")
        for check in result.checks:
            status = "ok" if check.passed else "FAIL"
            print(f"  {check.check_id}: {status} ({check.verdict})")
            if not check.passed and check.detail:
                print(f"    {check.detail[:500]}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
