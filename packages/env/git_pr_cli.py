from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

from orchestrator.git_outputs import maybe_open_gh_pr, run_branch_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Open a GitHub PR for a Nimbusware run branch (requires gh CLI).",
    )
    parser.add_argument("run_id", help="Run UUID")
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Git workspace root for the run",
    )
    parser.add_argument("--title", default=None)
    parser.add_argument("--body", default=None)
    args = parser.parse_args(argv)
    try:
        UUID(args.run_id)
    except ValueError:
        print(f"Invalid run_id: {args.run_id}", file=sys.stderr)
        return 2
    ws = args.workspace.expanduser().resolve()
    if not ws.is_dir():
        print(f"Workspace not found: {ws}", file=sys.stderr)
        return 2
    branch = run_branch_name(args.run_id)
    print(f"Branch: {branch}")
    result = maybe_open_gh_pr(ws, args.run_id, title=args.title, body=args.body)
    print(result)
    return 0 if result.get("status") == "created" else 1


if __name__ == "__main__":
    raise SystemExit(main())
