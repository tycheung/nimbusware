#!/usr/bin/env python3
"""Launch eval CLI — score attached workspace quality (deterministic rubric v0)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _evaluate_workspace(ws: Path, *, min_aggregate: float, use_llm: bool):
    sys.path.insert(0, str(REPO_ROOT / "packages"))
    from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

    if use_llm:
        os.environ["NIMBUSWARE_LAUNCH_EVAL_LLM"] = "1"
    return evaluate_workspace_rubric(ws, min_aggregate=min_aggregate)


def _run_matrix(*, min_aggregate: float, use_llm: bool) -> list[dict[str, object]]:
    sys.path.insert(0, str(REPO_ROOT / "packages"))
    from nimbusware_orchestrator.launch_eval_catalog import (
        default_workspace_paths,
        prompt_ids,
    )

    rows: list[dict[str, object]] = []
    for ws in default_workspace_paths(REPO_ROOT):
        if not ws.is_dir():
            continue
        scorecard = _evaluate_workspace(ws, min_aggregate=min_aggregate, use_llm=use_llm)
        rows.append(
            {
                "workspace": str(ws.relative_to(REPO_ROOT)).replace("\\", "/"),
                "prompt_catalog": list(prompt_ids(REPO_ROOT)),
                **scorecard.to_dict(),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate workspace launch readiness.")
    parser.add_argument("workspace", type=Path, nargs="?", help="Attached project workspace path")
    parser.add_argument("--min-aggregate", type=float, default=5.0)
    parser.add_argument("--json", action="store_true", help="Emit JSON scorecard")
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Score all catalog default_workspaces and emit JSON array",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Include opt-in advisory LLM panel findings (sets NIMBUSWARE_LAUNCH_EVAL_LLM=1)",
    )
    args = parser.parse_args(argv)

    if args.matrix:
        rows = _run_matrix(min_aggregate=args.min_aggregate, use_llm=args.llm)
        print(json.dumps(rows, indent=2))
        return 0 if len(rows) >= 1 else 1

    if args.workspace is None:
        parser.error("workspace required unless --matrix is set")

    ws = args.workspace.resolve()
    if not ws.is_dir():
        print(f"workspace not found: {ws}", file=sys.stderr)
        return 2
    scorecard = _evaluate_workspace(ws, min_aggregate=args.min_aggregate, use_llm=args.llm)
    if args.json:
        print(json.dumps(scorecard.to_dict(), indent=2))
    else:
        print(f"aggregate={scorecard.aggregate} passed={scorecard.passed}")
        for finding in scorecard.findings:
            print(f"  finding: {finding}")
        for finding in scorecard.llm_findings:
            print(f"  llm: {finding}")
    return 0 if scorecard.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
