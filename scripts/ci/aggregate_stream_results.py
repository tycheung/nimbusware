#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_result(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate JSON stream results from parallel CI jobs.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON files from run_stream.py --json or run_all_streams.py --json",
    )
    args = parser.parse_args()
    failed: list[str] = []
    for fp in args.files:
        path = Path(fp)
        data = _load_result(path)
        stream_id = str(data.get("stream_id") or path.stem)
        if data.get("passed", True):
            print(f"stream {stream_id}: ok")
            continue
        failed.append(stream_id)
        print(f"stream {stream_id}: FAIL", file=sys.stderr)
        for check in data.get("checks") or []:
            if not isinstance(check, dict):
                continue
            if check.get("passed", True):
                continue
            cid = check.get("check_id", "?")
            print(f"  {cid}: FAIL", file=sys.stderr)
    if failed:
        print(f"aggregate failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("aggregate: all streams passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
