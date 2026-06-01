from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimbusware_console import enterprise_console as ent_ui
from nimbusware_console.services import config_editors as cfg_svc
from nimbusware_console.services import custom_agents as agents_svc
from nimbusware_console.services import enterprise as enterprise_svc
from nimbusware_console.services import operator_chat as chat_svc
from nimbusware_maker.services import platform as platform_svc
from nimbusware_maker.services import projects as projects_svc


def test_operator_chat_create_run() -> None:
    with patch("nimbusware_console.services.operator_chat.post_response") as post:
        post.return_value = MagicMock(status_code=201)
        chat_svc.create_run({"workflow_profile": "default"})
    post.assert_called_once()
    assert post.call_args.kwargs["payload"] == {"workflow_profile": "default"}


def test_operator_chat_fetch_timeline() -> None:
    with patch("nimbusware_console.services.operator_chat.get_response") as get:
        get.return_value = MagicMock()
        chat_svc.fetch_timeline_response("rid")
    assert get.call_args.args[0] == "/runs/rid/timeline"


def test_config_editors_bundle_and_persona() -> None:
    with patch("nimbusware_console.services.config_editors.get_json") as get_json:
        get_json.return_value = {"bundles": []}
        assert cfg_svc.load_bundle_catalog() == {"bundles": []}
        get_json.assert_called_with("/bundles/catalog", timeout=10.0)
        get_json.return_value = {"personas": []}
        assert cfg_svc.load_persona_shelves() == {"personas": []}

    with patch("nimbusware_console.services.config_editors.patch_response") as patch_resp:
        patch_resp.return_value = MagicMock(json=lambda: {"ok": True})
        out = cfg_svc.patch_bundle("b1", {"name": "x"}, "tok")
        assert out == {"ok": True}
        cfg_svc.patch_persona("p1", {"name": "y"}, "tok")

    with patch("nimbusware_console.services.config_editors.delete_response") as delete:
        cfg_svc.delete_persona("p1", "tok")
    delete.assert_called_once()


def test_custom_agents_patch() -> None:
    with patch("nimbusware_console.services.custom_agents.patch_response") as patch_resp:
        agents_svc.patch_custom_agent("a1", {"system_prompt": "hi"})
    assert patch_resp.call_args.args[0] == "/custom-agents/a1"


def test_enterprise_manifest_helpers() -> None:
    assert not enterprise_svc.is_enterprise_edition_manifest(None)
    assert enterprise_svc.is_enterprise_edition_manifest({"edition": "enterprise"})
    assert not enterprise_svc.enterprise_console_feature_enabled({"edition": "individual"})
    enabled = enterprise_svc.enterprise_console_feature_enabled(
        {
            "edition": "enterprise",
            "features": {"enterprise_console": {"status": "enabled"}},
        },
    )
    assert enabled is True


def test_enterprise_fetch_with_api_key() -> None:
    with patch("nimbusware_console.services.enterprise.get_json") as get_json:
        get_json.return_value = {"tenants": []}
        enterprise_svc.fetch_tenants(api_key="secret")
    headers = get_json.call_args.kwargs.get("headers") or get_json.call_args[1].get("headers")
    assert headers is not None

    with patch("nimbusware_console.services.enterprise.get_json") as get_json:
        get_json.return_value = {"edition": "enterprise"}
        assert enterprise_svc.fetch_platform_edition()["edition"] == "enterprise"

    with patch("nimbusware_console.services.enterprise.get_json") as get_json:
        get_json.return_value = {"tenant_id": "t1"}
        enterprise_svc.fetch_fleet_memory_status(api_key="k")
        enterprise_svc.fetch_fleet_preflight_aggregate(api_key="k", limit=3)
        enterprise_svc.fetch_fleet_worker_health(api_key="k")
    assert get_json.call_count == 3


def test_enterprise_build_headers_empty() -> None:
    assert enterprise_svc.build_enterprise_headers(None) == {}
    assert enterprise_svc.build_enterprise_headers("  ") == {}


def test_enterprise_console_pure_helpers() -> None:
    opts = ent_ui.tenant_select_options(
        {"tenants": [{"slug": "acme", "display_name": "Acme Corp"}]},
    )
    assert opts == [("acme", "acme — Acme Corp")]
    key = ent_ui.resolve_active_api_key(
        primary_key="primary",
        tenant_keys={"acme": "tenant-key"},
        selected_tenant_slug="acme",
    )
    assert key == "tenant-key"
    rows = ent_ui.fleet_memory_status_table_rows({"tenant_id": "t1", "remote": {"configured": True}})
    assert any(r["field"] == "tenant_id" for r in rows)
    cap = ent_ui.fleet_worker_health_caption({"ok": True, "backpressure": "low"})
    assert cap and "ok=yes" in cap
    sli = ent_ui.fleet_sli_aggregate_caption(
        {"fleet_sli": {"combined_max_p95_latency_ms": 120, "sustained_export_present": True}},
    )
    assert sli and "combined_max_p95_ms=120" in sli
    exported = ent_ui.fleet_dashboard_export_json(memory={"a": 1}, preflight_aggregate=None, worker=None)
    assert '"fleet_memory"' in exported
    assert ent_ui.fleet_dashboard_export_filename_slug() == "enterprise_fleet_dashboard"


def test_maker_platform_and_projects() -> None:
    with patch("nimbusware_maker.services.platform.get_json") as get_json:
        get_json.return_value = {"status": "ready"}
        assert platform_svc.fetch_readiness()["status"] == "ready"

    with patch("nimbusware_maker.services.projects.post_json") as post_json:
        post_json.return_value = {"project_id": "p1"}
        out = projects_svc.create_project({"name": "App"})
        assert out["project_id"] == "p1"


def test_console_runs_service() -> None:
    from nimbusware_console.services import runs as runs_svc

    with patch("nimbusware_console.services.runs.get_json") as get_json:
        get_json.return_value = {"run_id": "r1"}
        assert runs_svc.fetch_run("r1")["run_id"] == "r1"
        runs_svc.fetch_timeline("r1")
        runs_svc.fetch_findings("r1")
    with patch("nimbusware_console.services.runs.get_response") as get_resp:
        get_resp.return_value = MagicMock(status_code=200)
        runs_svc.fetch_runs_list(params={"limit": 5})
    assert get_resp.call_args.kwargs["params"] == {"limit": 5}
    with patch("nimbusware_console.services.runs.post_json") as post_json:
        post_json.return_value = {"ok": True}
        runs_svc.post_retry("r1")
        runs_svc.post_escalate("r1", {"reason": "stuck"})
    assert post_json.call_count == 2


def test_maker_runs_service() -> None:
    from nimbusware_maker.services import runs as maker_runs_svc

    with patch("nimbusware_maker.services.runs.post_json") as post_json:
        post_json.return_value = {"run_id": "r2"}
        assert maker_runs_svc.create_run({"workflow_profile": "micro_slice"})["run_id"] == "r2"
        maker_runs_svc.approve_plan("r2")
        maker_runs_svc.prepare_slice("r2")
        maker_runs_svc.apply_slice("r2", {"slice_id": "s1"})
        maker_runs_svc.skip_slice("r2", {"slice_id": "s1"})
        maker_runs_svc.revert_workspace("r2")
    assert post_json.call_count == 6
    with patch("nimbusware_maker.services.runs.get_json") as get_json:
        get_json.return_value = {"pending": True}
        assert maker_runs_svc.fetch_pending("r2")["pending"] is True
        get_json.return_value = {"progress": 1}
        maker_runs_svc.fetch_maker_progress("r2", simple=False)
