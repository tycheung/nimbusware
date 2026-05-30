from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow

def test_openapi_info_description_present(client: TestClient) -> None:
    spec = client.app.openapi()
    desc = spec.get("info", {}).get("description", "")
    assert isinstance(desc, str) and len(desc.strip()) > 0
    assert "user" in desc.lower() and "admin" in desc.lower()


def test_openapi_problem_responses_include_problem_json_media_type(
    client: TestClient,
) -> None:
    spec = client.app.openapi()
    post422 = spec["paths"]["/v1/runs"]["post"]["responses"]["422"]["content"]
    assert "application/json" in post422
    assert "application/problem+json" in post422


def test_openapi_get_run_documents_optional_link_header(client: TestClient) -> None:
    spec = client.app.openapi()
    hdrs = (
        spec["paths"]["/v1/runs/{run_id}"]["get"]["responses"]["200"].get("headers") or {}
    )
    assert "Link" in hdrs
    assert "schema" in hdrs["Link"]


def test_get_run_includes_rfc5988_link_header(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get(f"/v1/runs/{rid}")
    assert r.status_code == 200
    link = r.headers.get("link") or r.headers.get("Link") or ""
    assert rid in link
    assert "timeline" in link
    assert "findings" in link


def test_openapi_timeline_documents_agent_evaluator_in_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/runs/{run_id}/timeline", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    schema = ok.get("content", {}).get("application/json", {}).get("schema", {})
    assert schema.get("$ref") == "#/components/schemas/RunTimelineResponse"
    tl_props = (
        spec.get("components", {})
        .get("schemas", {})
        .get("RunTimelineResponse", {})
        .get("properties", {})
    )
    assert "integrator_gate" in tl_props
    assert "integrator_gate_history" in tl_props
    assert "integrator_gate_delta" in tl_props
    assert "agent_evaluator" in tl_props
    desc = ok.get("description", "")
    assert "bundle_compatibility_ranking" in desc
    assert "evaluation_branch" in desc
    assert "llm_evaluation_summary" in desc
    assert "self_refinement" in tl_props
    assert "run_escalated" in tl_props
    assert "run_escalated_history" in tl_props
    assert "run_escalated_delta" in tl_props
    assert "security_scan_on_verify" in tl_props
    assert "security_scan_on_verify_history" in tl_props
    assert "self_refinement_marker_history" in tl_props
    assert "scraper_fetch" in tl_props
    assert "universal_critique" in tl_props


def test_openapi_timeline_and_findings_document_link_headers(client: TestClient) -> None:
    spec = client.app.openapi()
    tl = (
        spec["paths"]["/v1/runs/{run_id}/timeline"]["get"]["responses"]["200"]
        .get("headers")
        or {}
    )
    fd = (
        spec["paths"]["/v1/runs/{run_id}/findings"]["get"]["responses"]["200"]
        .get("headers")
        or {}
    )
    assert "Link" in tl and "schema" in tl["Link"]
    assert "Link" in fd and "schema" in fd["Link"]


def test_openapi_preflight_history_documents_sli_fields(client: TestClient) -> None:
    spec = client.app.openapi()
    props = (
        spec.get("paths", {})
        .get("/v1/preflight-history", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("properties", {})
    )
    assert "runs_with_preflight" in props
    assert "runs_without_preflight" in props
    assert "runs_with_p95_latency" in props
    assert "avg_p95_latency_ms" in props
    assert "max_p95_latency_ms" in props
    assert "preflight_coverage_ratio" in props
    assert "p95_latency_coverage_ratio" in props
    assert "runs_with_multisample_preflight" in props
    assert "runs_with_checks_passed" in props
    assert "distinct_validated_model_id_count" in props
    metrics_export = props.get("metrics_export", {})
    export_props = metrics_export.get("properties", {})
    assert "export_schema_version" in export_props
    assert "export_window_consistent" in export_props
    params = (
        spec.get("paths", {})
        .get("/v1/preflight-history", {})
        .get("get", {})
        .get("parameters", [])
    )
    param_names = {p.get("name") for p in params if isinstance(p, dict)}
    assert "include_metrics_export" in param_names


def test_openapi_preflight_history_include_metrics_export_param_description(
    client: TestClient,
) -> None:
    spec = client.app.openapi()
    params = (
        spec.get("paths", {})
        .get("/v1/preflight-history", {})
        .get("get", {})
        .get("parameters", [])
    )
    by_name = {
        p.get("name"): p
        for p in params
        if isinstance(p, dict) and isinstance(p.get("name"), str)
    }
    desc = by_name.get("include_metrics_export", {}).get("description", "")
    assert "export_schema_version" in desc
    assert "export_window_consistent" in desc


def _openapi_path_response_content(spec: dict, path: str, method: str, status: str) -> dict:
    return (
        spec.get("paths", {})
        .get(path, {})
        .get(method, {})
        .get("responses", {})
        .get(status, {})
        .get("content", {})
        or {}
    )


def test_openapi_preflight_and_scraper_inventory_document_500_problem_json(
    client: TestClient,
) -> None:
    spec = client.app.openapi()
    for path in ("/v1/preflight-history", "/v1/scraper-artifacts/inventory"):
        content = _openapi_path_response_content(spec, path, "get", "500")
        assert "application/json" in content
        assert "application/problem+json" in content
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


def test_openapi_scraper_inventory_documents_retention_fields(client: TestClient) -> None:
    spec = client.app.openapi()
    props = (
        spec.get("paths", {})
        .get("/v1/scraper-artifacts/inventory", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("properties", {})
    )
    assert "oldest_mtime_iso" in props
    assert "newest_mtime_iso" in props
    assert "retention_max_age_days" in props
    assert "retention_stale_file_count" in props
    assert "retention_stale_bytes" in props
    assert "storage_backend" in props
    assert "object_store_configured" in props
    assert "object_store_ready" in props
    assert "object_store_prune_requested" in props
    assert "object_store_prune_effective" in props
    assert "retention_execution_mode" in props
    assert "retention_alert_level" in props


def test_timeline_and_findings_include_rfc5988_link_headers(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    t = client.get(f"/v1/runs/{rid}/timeline")
    assert t.status_code == 200
    tl = t.headers.get("link") or t.headers.get("Link") or ""
    assert rid in tl
    assert 'rel="run"' in tl
    assert "findings" in tl
    f = client.get(f"/v1/runs/{rid}/findings")
    assert f.status_code == 200
    fl = f.headers.get("link") or f.headers.get("Link") or ""
    assert rid in fl
    assert 'rel="run"' in fl
    assert "timeline" in fl


def test_openapi_documents_user_and_admin_access_tags(client: TestClient) -> None:
    spec = client.app.openapi()
    tag_names = {t["name"] for t in spec.get("tags", []) if isinstance(t, dict)}
    assert "user" in tag_names
    assert "admin" in tag_names
    assert "x-tagGroups" in spec
    groups = {g["name"]: g["tags"] for g in spec["x-tagGroups"]}
    assert groups["User routes (Maker)"] == ["user"]
    assert groups["Admin routes (Admin Console)"] == ["admin"]

    post_project = spec["paths"]["/v1/projects"]["post"]
    assert post_project["tags"][0] == "user"

    delete_project = spec["paths"]["/v1/projects/{project_id}"]["delete"]
    assert delete_project["tags"][0] == "admin"

    post_run = spec["paths"]["/v1/runs"]["post"]
    assert post_run["tags"][0] == "user"

    lifecycle = spec["paths"]["/v1/runs/{run_id}/lifecycle/start"]["post"]
    assert lifecycle["tags"][0] == "admin"

