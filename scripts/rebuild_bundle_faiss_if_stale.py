#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Nimbusware repository root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print whether rebuild would run without executing",
    )
    args = parser.parse_args()
    repo = args.repo_root.resolve()

    from nimbusware_extensions.catalog import bundle_faiss_index_sync_state

    state = bundle_faiss_index_sync_state(repo)
    stale = state.get("stale")
    if stale is not True:
        print(
            f"FAISS index fresh or not comparable (ready={state.get('ready')}, stale={stale})",
        )
        return 0

    build = repo / "scripts" / "build_bundle_faiss_index.py"
    if not build.is_file():
        print(f"Missing {build}", file=sys.stderr)
        return 1
    if args.dry_run:
        print("Would rebuild: poetry run python scripts/build_bundle_faiss_index.py")
        return 0

    cmd = [sys.executable, str(build), "--repo-root", str(repo)]
    print("Rebuilding stale FAISS index...")
    return subprocess.call(cmd, cwd=str(repo))


if __name__ == "__main__":
    raise SystemExit(main())
