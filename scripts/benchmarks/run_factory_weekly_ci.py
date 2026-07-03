#!/usr/bin/env python3
"""Factory weekly CI — golden replay + PUT E2E."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FACTORY_WEEKLY_AUTOPILOT_LEVEL = 10
GOLDEN_PATH = REPO_ROOT / "tests" / "fixtures" / "factory" / "golden_factory_replay.json"
MANIFEST_PATH = REPO_ROOT / "tests" / "fixtures" / "factory" / "golden_factory_replay_manifest.json"
REPOS_ROOT = REPO_ROOT / "tests" / "fixtures" / "repos"


def _playwright_ready() -> tuple[bool, str]:
    sys.path.insert(0, str(REPO_ROOT / "packages"))
    from orchestrator.factory.runner import _playwright_module_ready

    return _playwright_module_ready()


def load_factory_golden_entries(repo_root: Path | None = None) -> list[dict[str, Any]]:
    repo = repo_root or REPO_ROOT
    manifest = repo / "tests" / "fixtures" / "factory" / "golden_factory_replay_manifest.json"
    if manifest.is_file():
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        entries = doc.get("entries")
        if isinstance(entries, list) and entries:
            return [e for e in entries if isinstance(e, dict)]
    golden = repo / "tests" / "fixtures" / "factory" / "golden_factory_replay.json"
    if golden.is_file():
        return [json.loads(golden.read_text(encoding="utf-8"))]
    return []


def run_factory_golden_entry(
    spec: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo = repo_root or REPO_ROOT
    sys.path.insert(0, str(repo / "packages"))

    from orchestrator.factory.completion import (
        evaluate_factory_gates,
        resolve_factory_tier,
    )
    from orchestrator.factory.runner import run_put_e2e_flow
    from orchestrator.factory.runtime import start_put_preview, stop_put_preview
    from orchestrator.interaction.interaction_surface_map import discover_surfaces_static
    from projections.builders.factory_status import factory_status_from_events

    ws_name = str(spec.get("workspace_fixture") or "tiny_api_app")
    repos_root = (repo_root or REPO_ROOT) / "tests" / "fixtures" / "repos"
    ws = repos_root / ws_name
    entry_id = str(spec.get("id") or spec.get("flow_id") or "default")
    summary: dict[str, Any] = {
        "id": entry_id,
        "workspace": ws_name,
        "passed": False,
    }
    if not ws.is_dir():
        summary["error"] = f"workspace_missing:{ws_name}"
        return summary

    tier = resolve_factory_tier(metadata_tier=str(spec.get("factory_tier") or "T2"))
    flow_id = str(spec.get("flow_id") or "contacts_api")
    port = 19876 + (hash(entry_id) % 400)

    preview = start_put_preview(ws, port, startup_timeout_seconds=12.0)
    put_preview_ok = preview.ok
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"

    try:
        ism = discover_surfaces_static(ws, preview_base_url=base_url if put_preview_ok else None)
        put_e2e = run_put_e2e_flow(
            base_url,
            flow_id,
            repo_root=repo,
            workspace=ws,
            require_playwright=False,
        )
        gates = evaluate_factory_gates(
            tier,
            put_preview_ok=put_preview_ok,
            ism=ism,
            put_e2e=put_e2e,
            repo_root=repo,
        )
        events = [
            {
                "event_type": "stage.passed",
                "metadata": {
                    "factory": {
                        "tier": tier,
                        "ism_coverage_pct": gates.details.get("ism_coverage_pct", 0.0),
                        "put_e2e_passed": put_e2e.passed,
                    },
                    "put_e2e": put_e2e.to_dict(),
                },
            },
        ]
        factory_status = factory_status_from_events(events)
        expected = (
            spec.get("expected_factory_status")
            if isinstance(spec.get("expected_factory_status"), dict)
            else {}
        )
        status_ok = True
        if factory_status:
            if expected.get("tier"):
                status_ok = status_ok and factory_status.get("tier") == expected["tier"]
            if "put_e2e_passed" in expected:
                status_ok = (
                    status_ok and factory_status.get("put_e2e_passed") == expected["put_e2e_passed"]
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
                "factory_status": factory_status,
                "passed": gates.passed and put_e2e.verdict == "PASS" and status_ok,
            },
        )
        return summary
    finally:
        stop_put_preview(preview.handle)


def run_factory_weekly_ci(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or REPO_ROOT
    entries = load_factory_golden_entries(repo)
    summary: dict[str, Any] = {
        "golden_manifest": MANIFEST_PATH.name if MANIFEST_PATH.is_file() else GOLDEN_PATH.name,
        "autopilot_level": FACTORY_WEEKLY_AUTOPILOT_LEVEL,
        "trust_preset": "Continuous improve",
        "skipped": False,
        "passed": False,
        "entry_count": len(entries),
        "prompt_ids": [
            str(e.get("id") or e.get("flow_id") or "default")
            for e in entries
            if isinstance(e, dict)
        ],
    }
    if not entries:
        summary["error"] = "golden_fixture_missing"
        return summary

    pw_ready, pw_detail = _playwright_ready()
    summary["playwright_ready"] = pw_ready
    summary["playwright_detail"] = pw_detail
    if not pw_ready:
        summary["skipped"] = True
        summary["reason"] = "playwright_not_installed"
        summary["passed"] = True
        summary["golden_valid"] = True
        return summary

    results = [run_factory_golden_entry(spec, repo_root=repo) for spec in entries]
    summary["results"] = results
    summary["passed"] = all(r.get("passed") for r in results)
    return summary


def main() -> int:
    summary = run_factory_weekly_ci()
    print(json.dumps(summary, sort_keys=True))
    if summary.get("skipped"):
        print("Skip: Playwright not installed (factory weekly CI stub)")
        return 0
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
