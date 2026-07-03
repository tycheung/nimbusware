from __future__ import annotations

from pathlib import Path

from orchestrator.factory.completion import evaluate_factory_gates, resolve_factory_tier
from orchestrator.factory.runner import run_put_e2e_flow
from orchestrator.factory.runtime import start_put_preview, stop_put_preview
from orchestrator.interaction.interaction_surface_map import discover_surfaces_static
from orchestrator.workflow.campaign import parse_completion_workflow_block

REPO = Path(__file__).resolve().parents[2]
WS = REPO / "tests" / "fixtures" / "repos" / "tiny_api_app"


def test_campaign_factory_t3_profile_parses() -> None:
    block = parse_completion_workflow_block(REPO, "campaign_factory_t3")
    assert block.factory_tier == "T3"


def test_t3_factory_gates_pass_on_todo_api_flow() -> None:
    tier = resolve_factory_tier(metadata_tier="T3")
    port = 19878
    preview = start_put_preview(WS, port, startup_timeout_seconds=12.0)
    assert preview.ok
    base_url = preview.handle.base_url if preview.handle else f"http://127.0.0.1:{port}"
    try:
        ism = discover_surfaces_static(WS, preview_base_url=base_url)
        put_e2e = run_put_e2e_flow(base_url, "todo_api", repo_root=REPO, require_playwright=False)
        assert put_e2e.verdict == "PASS", put_e2e.detail
        gates = evaluate_factory_gates(
            tier,
            put_preview_ok=True,
            ism=ism,
            put_e2e=put_e2e,
            repo_root=REPO,
        )
        assert gates.passed is True, gates.blocking
        assert (gates.details.get("ism_coverage_pct") or 0) >= 50.0
    finally:
        stop_put_preview(preview.handle)
