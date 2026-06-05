#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="self_refinement_production_ungated",
        help="Workflow profile with self_refinement + llm_critique_enabled",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Nimbusware repository root",
    )
    args = parser.parse_args()
    os.environ.setdefault("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER", "1")
    os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(args.repo_root.resolve()))

    from nimbusware_orchestrator.pipeline import make_dev_orchestrator
    from nimbusware_orchestrator.workflow_self_refinement import (
        self_refinement_production_llm_critique_effective,
    )

    if not self_refinement_production_llm_critique_effective(
        args.repo_root,
        args.profile,
    ):
        print(
            f"Profile {args.profile!r} does not enable production SR LLM; "
            "check workflow YAML.",
            file=sys.stderr,
        )
        return 2

    orch, mem = make_dev_orchestrator(repo_root=args.repo_root)
    rid = orch.create_run(args.profile)
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    orch._maybe_continue_ungated_self_refinement_loop(rid)  # noqa: SLF001
    signals = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "self_refinement.loop.signalled"
    ]
    llm_attempted = any(
        ((s.get("payload") or {}).get("llm_critique_attempted") is True) for s in signals
    )
    print(f"run_id={rid} loop_signals={len(signals)} llm_critique_attempted={llm_attempted}")
    return 0 if signals else 1


if __name__ == "__main__":
    raise SystemExit(main())
