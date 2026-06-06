#!/usr/bin/env python3
"""Launch eval CLI — score attached workspace quality (deterministic rubric v0)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate workspace launch readiness.")
    parser.add_argument("workspace", type=Path, help="Attached project workspace path")
    parser.add_argument("--min-aggregate", type=float, default=5.0)
    parser.add_argument("--json", action="store_true", help="Emit JSON scorecard")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Include opt-in advisory LLM panel findings (sets NIMBUSWARE_LAUNCH_EVAL_LLM=1)",
    )
    args = parser.parse_args(argv)

    if args.llm:
        os.environ["NIMBUSWARE_LAUNCH_EVAL_LLM"] = "1"

    sys.path.insert(0, str(REPO_ROOT / "packages"))
    from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

    ws = args.workspace.resolve()
    if not ws.is_dir():
        print(f"workspace not found: {ws}", file=sys.stderr)
        return 2
    scorecard = evaluate_workspace_rubric(ws, min_aggregate=args.min_aggregate)
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
