#!/usr/bin/env python3
"""Opt-in PR PUT E2E gate — catalog flows against fixture workspaces."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPOS_ROOT = REPO_ROOT / "tests" / "fixtures" / "repos"


def run_put_e2e_ci_gate(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or REPO_ROOT
    sys.path.insert(0, str(repo / "packages"))

    from nimbusware_orchestrator.factory_completion import (
        evaluate_factory_gates,
        resolve_factory_tier,
    )
    from nimbusware_orchestrator.interaction_surface_map import discover_surfaces_static
    from nimbusware_orchestrator.put_e2e_runner import run_put_e2e_flow
    from nimbusware_orchestrator.put_runtime import start_put_preview, stop_put_preview

    ws = REPOS_ROOT / "tiny_api_app"
    summary: dict[str, Any] = {"workspace": ws.name, "skipped": False, "passed": False}
    if not ws.is_dir():
        summary["error"] = "workspace_missing:tiny_api_app"
        return summary

    tier = resolve_factory_tier(metadata_tier="T2")
    flow_id = "contacts_api"
    port = 19877
    preview = start_put_preview(ws, port, startup_timeout_seconds=12.0)
    put_preview_ok = preview.ok
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    try:
        ism = discover_surfaces_static(ws, preview_base_url=base_url if put_preview_ok else None)
        put_e2e = run_put_e2e_flow(
            base_url,
            flow_id,
            repo_root=repo,
            require_playwright=False,
        )
        gates = evaluate_factory_gates(
            tier,
            put_preview_ok=put_preview_ok,
            ism=ism,
            put_e2e=put_e2e,
            repo_root=repo,
        )
        summary.update(
            {
                "tier": tier,
                "flow_id": flow_id,
                "put_preview_ok": put_preview_ok,
                "put_e2e": put_e2e.to_dict(),
                "factory_gates": {
                    "passed": gates.passed,
                    "blocking": list(gates.blocking),
                },
                "passed": gates.passed and put_e2e.verdict == "PASS",
            },
        )
        return summary
    finally:
        stop_put_preview(preview.handle)


def main() -> int:
    summary = run_put_e2e_ci_gate()
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
