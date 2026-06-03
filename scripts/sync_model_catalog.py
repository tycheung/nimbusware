#!/usr/bin/env python3
"""Offline helper: refresh configs/hardware/model_catalog.json from a local JSON export."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from nimbusware_env import find_repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync hardware model catalog subset")
    parser.add_argument("source", type=Path, help="Path to source JSON with models[]")
    args = parser.parse_args()
    root = find_repo_root()
    dest = root / "configs" / "hardware" / "model_catalog.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, dest)
    doc = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(doc.get("models"), list):
        raise SystemExit("source must contain models array")
    print(f"Wrote {dest} ({len(doc['models'])} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
