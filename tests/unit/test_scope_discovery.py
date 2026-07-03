from __future__ import annotations

from maker.autopilot_defer_matrix import autopilot_may_auto_defer
from maker.intent.scope_discovery import (
    discovery_complete_for_start,
    recommend_for_me,
    scope_discover,
    scope_gather,
    scope_narrowed_to_backend_only,
)


def test_scope_narrowed_backend_only() -> None:
    assert scope_narrowed_to_backend_only("Build a REST API for todos, backend only")
    assert not scope_narrowed_to_backend_only("Build a todo app with web UI")


def test_scope_discover_emits_questions() -> None:
    state = scope_discover("Build a todo app")
    assert state["discovery_complete"] is False
    assert len(state["questions_emitted"]) >= 3
    assert state["surfaces_likely"] == ["api", "web"]


def test_scope_discover_questions_include_hints() -> None:
    state = scope_discover("Build a todo app")
    by_id = {q["id"]: q for q in state["questions_emitted"]}
    assert "hint" in by_id["client_form"]
    assert "Web app" in by_id["client_form"]["hint"]


def test_scope_discover_skips_questions_when_narrowed() -> None:
    state = scope_discover("Build a REST API, backend only")
    assert state["discovery_complete"] is True
    assert state["questions_emitted"] == []
    assert state["stack_manifest"]["surfaces"] == ["api"]


def test_recommend_for_me_completes_discovery() -> None:
    state = scope_discover("Build a todo app")
    recommended = recommend_for_me(state)
    assert recommended["discovery_complete"] is True
    assert recommended["stack_manifest"]["surfaces"] == ["api", "web"]
    assert recommended["recommend_for_me"] is True


def test_scope_gather_with_client_form() -> None:
    state = scope_discover("Build a todo app")
    gathered = scope_gather(
        state,
        [{"question_id": "client_form", "answer": "Web app"}],
    )
    assert gathered["discovery_complete"] is True
    assert "web" in gathered["stack_manifest"]["surfaces"]


def test_recommend_for_me_applies_regulated_stack_guard(tmp_path, monkeypatch) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_stack_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  regulated:\n    allowed_stacks:\n      api: fastapi_python\n      web: react_vite\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "env.find_repo_root",
        lambda: tmp_path,
    )
    state = scope_discover("Build a todo app")
    recommended = recommend_for_me(state, tenant_slug="regulated")
    assert recommended["stack_manifest"]["stacks"]["api"] == "fastapi_python"
    assert recommended["stack_manifest"]["stacks"]["web"] == "react_vite"


def test_manifest_from_answers_clamps_backend_stack_for_regulated_tenant(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_stack_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  regulated:\n    allowed_stacks:\n      api: fastapi_python\n      web: react_vite\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "env.find_repo_root",
        lambda: tmp_path,
    )
    state = scope_discover("Build a todo app")
    gathered = scope_gather(
        state,
        [
            {"question_id": "client_form", "answer": "Web app"},
            {"question_id": "backend_stack", "answer": "Node express"},
        ],
        tenant_slug="regulated",
    )
    assert gathered["stack_manifest"]["stacks"]["api"] == "fastapi_python"


def test_discovery_gate_blocks_fullstack_without_scope() -> None:
    ok, detail = discovery_complete_for_start(
        {"business_prompt": "Build a todo app"},
        workflow_profile="campaign_fullstack",
    )
    assert ok is False
    assert detail


def test_discovery_gate_allows_recommend_for_me() -> None:
    ok, _ = discovery_complete_for_start(
        {"business_prompt": "Build a todo app", "recommend_for_me": True},
        workflow_profile="campaign_fullstack",
    )
    assert ok is True


def test_discovery_gate_blocks_enterprise_required_fields(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SETUP_BUNDLE", "enterprise")
    ok, detail = discovery_complete_for_start(
        {
            "business_prompt": "Build a todo app",
            "scope_discovery": {
                "discovery_complete": True,
                "answers": {"client_form": "Web app"},
            },
        },
        workflow_profile="campaign_fullstack",
        tenant_slug="regulated",
    )
    assert ok is False
    assert detail
    assert "hosting" in detail


def test_discovery_gate_allows_enterprise_when_required_fields_answered(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SETUP_BUNDLE", "enterprise")
    ok, _ = discovery_complete_for_start(
        {
            "business_prompt": "Build a todo app",
            "scope_discovery": {
                "discovery_complete": True,
                "answers": {
                    "client_form": "Web app",
                    "hosting": "AWS",
                    "data_residency": "US only",
                },
            },
        },
        workflow_profile="campaign_fullstack",
        tenant_slug="regulated",
    )
    assert ok is True


def test_discovery_gate_applies_to_safe_coding_campaign_fullstack() -> None:
    ok, detail = discovery_complete_for_start(
        {"business_prompt": "Build a todo app"},
        workflow_profile="safe_coding_campaign_fullstack",
    )
    assert ok is False
    assert detail


def test_discovery_gate_allows_micro_slice_profile() -> None:
    ok, _ = discovery_complete_for_start(
        {"business_prompt": "Build a todo app"},
        workflow_profile="campaign_micro_slice",
    )
    assert ok is True


def test_autopilot_defer_matrix_safe_coding() -> None:
    assert autopilot_may_auto_defer(archetype="safe_coding") is False


def test_autopilot_defer_matrix_engineer_trust() -> None:
    assert autopilot_may_auto_defer(archetype="engineer_workspace", trust_score=8.0) is True
    assert autopilot_may_auto_defer(archetype="engineer_workspace", trust_score=5.0) is False


def test_autopilot_defer_matrix_enterprise_hosting() -> None:
    assert (
        autopilot_may_auto_defer(
            setup_bundle="enterprise",
            field_id="hosting",
        )
        is False
    )
