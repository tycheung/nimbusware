from __future__ import annotations

import json
from pathlib import Path

from agent_core.models.backlog import SliceStatus
from nimbusware_orchestrator.backlog_generator import generate_heuristic_backlog
from nimbusware_orchestrator.factory_completion import (
    PUT_E2E_FIX_CATEGORY,
    append_put_e2e_fix_slice,
    build_put_e2e_fix_slice,
    evaluate_factory_gates,
    handle_put_e2e_failure,
    load_factory_tier_policy,
    resolve_factory_tier,
    tier_config,
)
from nimbusware_orchestrator.interaction_surface_critic import critique_interaction_surfaces
from nimbusware_orchestrator.interaction_surface_map import (
    InteractionSurfaceMap,
    ISMSurface,
)
from nimbusware_orchestrator.put_e2e_runner import PutE2EFinding, PutE2EResult
from nimbusware_projections.builders.factory_status import factory_status_from_events
from nimbusware_projections.builders.maker_progress import maker_progress_from_events

REPO = Path(__file__).resolve().parents[2]


def test_load_factory_tier_policy_has_tiers() -> None:
    doc = load_factory_tier_policy(REPO)
    tiers = doc.get("factory_tiers")
    assert isinstance(tiers, dict)
    assert "T0" in tiers and "T3" in tiers


def test_tier_config_t0_uses_static_ism() -> None:
    cfg = tier_config("T0", REPO)
    assert cfg.get("ism_discovery") == "static"


def test_tier_config_t2_enables_preview() -> None:
    cfg = tier_config("T2", REPO)
    assert cfg.get("put_preview_enabled") is True
    assert cfg.get("ism_discovery") == "openapi"


def test_resolve_factory_tier_prefers_metadata() -> None:
    assert resolve_factory_tier(metadata_tier="T3", env_tier="T1") == "T3"
    assert resolve_factory_tier(env_tier="t2") == "T2"


def test_evaluate_factory_gates_t0_passes_without_preview() -> None:
    result = evaluate_factory_gates("T0", put_preview_ok=None, repo_root=REPO)
    assert result.passed is True
    assert result.tier == "T0"


def test_evaluate_factory_gates_t2_requires_put_e2e_pass() -> None:
    ism = InteractionSurfaceMap(
        surfaces=[
            ISMSurface(surface_id="openapi:GET:/health", kind="openapi_path", path="/health")
        ],
        source="openapi",
    )
    fail_e2e = PutE2EResult(
        verdict="FAIL", flow_id="crm", base_url="http://127.0.0.1:1", detail="boom"
    )
    result = evaluate_factory_gates(
        "T2", put_preview_ok=True, ism=ism, put_e2e=fail_e2e, repo_root=REPO
    )
    assert result.passed is False
    assert "put_e2e_failed" in result.blocking


def test_evaluate_factory_gates_t2_passes_with_e2e() -> None:
    ism = InteractionSurfaceMap(
        surfaces=[
            ISMSurface(surface_id="openapi:GET:/health", kind="openapi_path", path="/health")
        ],
        source="openapi",
    )
    ok_e2e = PutE2EResult(
        verdict="PASS",
        flow_id="crm",
        base_url="http://127.0.0.1:1",
        exercised_paths={"/health"},
    )
    result = evaluate_factory_gates(
        "T2", put_preview_ok=True, ism=ism, put_e2e=ok_e2e, repo_root=REPO
    )
    assert result.passed is True
    assert result.details.get("ism_coverage_pct") == 100.0


def test_build_put_e2e_fix_slice_category() -> None:
    findings = [
        PutE2EFinding(kind="step_fail", message="health check failed", surface_path="/health")
    ]
    sl = build_put_e2e_fix_slice(findings, flow_id="crm")
    assert PUT_E2E_FIX_CATEGORY in sl.rationale
    assert sl.status == SliceStatus.PENDING


def test_append_put_e2e_fix_slice_increments_backlog() -> None:
    backlog = generate_heuristic_backlog("camp-1", max_slices=2)
    before = backlog.metadata.total_slices_planned
    revised = append_put_e2e_fix_slice(
        backlog,
        [PutE2EFinding(kind="step_fail", message="fail")],
        flow_id="todo_api",
    )
    assert revised.metadata.total_slices_planned == before + 1


def test_handle_put_e2e_failure_only_on_fail() -> None:
    backlog = generate_heuristic_backlog("camp-2", max_slices=1)
    ok = PutE2EResult(verdict="PASS", flow_id="crm", base_url="http://x")
    assert handle_put_e2e_failure(backlog, ok) is backlog
    fail = PutE2EResult(
        verdict="FAIL",
        flow_id="crm",
        base_url="http://x",
        findings=[PutE2EFinding(kind="step_fail", message="x")],
    )
    fixed = handle_put_e2e_failure(backlog, fail)
    assert fixed is not None
    assert fixed.metadata.total_slices_planned == backlog.metadata.total_slices_planned + 1


def test_interaction_surface_critic_uncovered() -> None:
    ism = InteractionSurfaceMap(
        surfaces=[
            ISMSurface(surface_id="link:/", kind="html_link", path="/"),
            ISMSurface(surface_id="link:/about", kind="html_link", path="/about"),
        ],
        source="html",
    )
    findings = critique_interaction_surfaces(ism, exercised={"/"}, tier="T2", min_coverage_pct=80.0)
    kinds = {f["kind"] for f in findings}
    assert "ism_low_coverage" in kinds
    assert "ism_uncovered_surface" in kinds


def test_factory_status_from_events() -> None:
    events = [
        {
            "event_type": "stage.passed",
            "metadata": {
                "factory": {"tier": "T2", "ism_coverage_pct": 75.0, "put_e2e_passed": True},
            },
        },
    ]
    status = factory_status_from_events(events)
    assert status["tier"] == "T2"
    assert status["ism_coverage_pct"] == 75.0
    assert status["put_e2e_passed"] is True
    assert "tier_promotion" in status


def test_maker_progress_includes_factory_status() -> None:
    events = [
        {"event_type": "run.created", "metadata": {"requirements": {"business_prompt": "CRM"}}},
        {
            "event_type": "stage.passed",
            "metadata": {
                "factory": {"tier": "T1", "ism_coverage_pct": 10.0, "put_e2e_passed": False},
            },
        },
    ]
    body = maker_progress_from_events(events)
    fs = body.get("factory_status")
    assert fs["tier"] == "T1"
    assert fs["ism_coverage_pct"] == 10.0
    assert fs["put_e2e_passed"] is False
    assert fs.get("tier_promotion", {}).get("remaining_gates")


def test_golden_factory_replay_fixture_loads() -> None:
    path = REPO / "tests" / "fixtures" / "factory" / "golden_factory_replay.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert spec["flow_id"] == "contacts_api"
    assert spec["factory_tier"] == "T2"
