from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("HERMES_ADMIN_TOKEN", "test-admin-token")

from agent_core.models import (  # noqa: E402
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from hermes_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_openapi_includes_tag_descriptions(client: TestClient) -> None:
    spec = client.app.openapi()
    tags = {t["name"]: str(t.get("description", "")) for t in spec.get("tags", [])}
    assert "runs" in tags and len(tags["runs"]) > 10
    assert "actions" in tags and len(tags["actions"]) > 5
    assert "bundles" in tags and "bundle" in tags["bundles"].lower()
    assert "faiss_index_ready" in tags["bundles"]
    assert "bounded" in tags["bundles"].lower() and "k" in tags["bundles"]
    assert "personas" in tags and "persona" in tags["personas"].lower()


def test_get_bundle_search_returns_hits(client: TestClient) -> None:
    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body.get("query") == "auth"
    assert body.get("k") == 5
    hits = body.get("hits") or []
    ids = {h.get("id") for h in hits if isinstance(h, dict)}
    assert "auth-rbac-starter" in ids


def test_get_bundle_search_echoes_default_k_when_omitted(client: TestClient) -> None:
    """``k`` defaults to 5 on the route; the response must echo that same default."""
    r = client.get("/v1/bundles/search", params={"q": "auth"})
    assert r.status_code == 200
    assert r.json().get("k") == 5


def test_get_bundle_search_echoes_custom_k(client: TestClient) -> None:
    """API echoes the bounded ``k`` from the request, mirroring the console payload."""
    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 3})
    assert r.status_code == 200
    assert r.json().get("k") == 3


def test_get_bundle_search_openapi_documents_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/bundles/search", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    ex = (
        ok.get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex.get("query") == "auth"
    assert ex.get("k") == 5
    assert isinstance(ex.get("hits"), list) and ex["hits"]
    assert ex["hits"][0].get("id") == "auth-rbac-starter"
    assert "faiss_index_ready" in ex
    assert isinstance(ex["faiss_index_ready"], bool)
    props = (
        spec.get("components", {})
        .get("schemas", {})
        .get("BundleSearchResponse", {})
        .get("properties", {})
    )
    assert "faiss_index_stale" in props


def test_get_bundle_search_reports_faiss_index_ready_bool(client: TestClient) -> None:
    """``faiss_index_ready`` / ``faiss_index_stale`` mirror on-disk FAISS sync helpers."""
    from hermes_extensions.catalog import (
        bundle_faiss_index_ready,
        bundle_faiss_index_sync_state,
    )

    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert "faiss_index_ready" in body
    assert isinstance(body["faiss_index_ready"], bool)
    assert "faiss_index_stale" in body
    repo_root = Path(os.environ["HERMES_REPO_ROOT"])
    assert body["faiss_index_ready"] is bundle_faiss_index_ready(repo_root)
    assert body["faiss_index_stale"] == bundle_faiss_index_sync_state(repo_root).get("stale")


def test_get_bundle_search_uses_db_materialized_catalog(client: TestClient) -> None:
    from hermes_api.deps import get_orchestrator

    class _Mat:
        use_db = True

        @staticmethod
        def get_bundle_catalog() -> dict[str, object]:
            return {
                "version": 1,
                "bundles": [
                    {"id": "db-only-bundle", "title": "DB Bundle", "tags": ["db", "catalog"]},
                ],
                "workflow_bundle_map": {"default": "db-only-bundle"},
            }

    class _Orch:
        def __init__(self, root: Path) -> None:
            self.repo_root = root
            self.config_materializer = _Mat()

    app.dependency_overrides[get_orchestrator] = lambda: _Orch(Path(os.environ["HERMES_REPO_ROOT"]))
    try:
        r = client.get("/v1/bundles/search", params={"q": "db", "k": 5})
        assert r.status_code == 200
        body = r.json()
        ids = {h.get("id") for h in (body.get("hits") or []) if isinstance(h, dict)}
        assert "db-only-bundle" in ids
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)


def test_get_persona_shelves_returns_catalog(client: TestClient) -> None:
    r = client.get("/v1/personas")
    assert r.status_code == 200
    body = r.json()
    assert body.get("version") == 1
    ba = body.get("business_area") or []
    dr = body.get("development_role") or []
    ba_ids = {e.get("id") for e in ba if isinstance(e, dict)}
    dr_ids = {e.get("id") for e in dr if isinstance(e, dict)}
    assert "commerce" in ba_ids
    assert "backend_engineer" in dr_ids


def test_get_persona_shelves_openapi_documents_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/personas", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    ex = (
        ok.get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex.get("version") == 1
    assert isinstance(ex.get("business_area"), list) and ex["business_area"]
    assert ex["business_area"][0].get("id") == "commerce"


def test_persona_edit_round_trip_through_event_store(tmp_path: Path) -> None:
    """fo127 #14-edit: PATCH a persona, verify GET reflects it AND audit event lands.

    Drives the full API surface — POST + PATCH + GET — against an isolated
    tmp shelves.yaml plus an InMemoryEventStore so we exercise the wiring end
    to end without touching the real repo.
    """
    import yaml as _yaml  # local import keeps test module imports tidy

    from hermes_api.deps import get_orchestrator, get_store
    from hermes_store.memory import InMemoryEventStore

    personas_dir = tmp_path / "configs" / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)
    (personas_dir / "shelves.yaml").write_text(
        _yaml.safe_dump(
            {
                "version": 1,
                "business_area": [{"id": "commerce", "display_name": "C", "version": 1}],
                "development_role": [{"id": "be", "display_name": "BE", "version": 1}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    class _Orch:
        def __init__(self, root: Path) -> None:
            self.repo_root = root

    store = InMemoryEventStore()
    app.dependency_overrides[get_orchestrator] = lambda: _Orch(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as c:
            patch_body = {
                "expected_version": 1,
                "instructions": "Refund policy required.",
                "actor": "alice",
            }
            r = c.patch(
                "/v1/personas/business_area/commerce",
                json=patch_body,
                headers={"X-Hermes-Admin-Token": "test-admin-token"},
            )
            assert r.status_code == 200, r.text
            patched = next(
                e for e in r.json()["business_area"] if e["id"] == "commerce"
            )
            assert patched["instructions"] == "Refund policy required."
            assert patched["version"] == 2

            g = c.get("/v1/personas")
            assert g.status_code == 200
            on_wire = next(
                e for e in g.json()["business_area"] if e["id"] == "commerce"
            )
            assert on_wire["instructions"] == "Refund policy required."
            assert on_wire["version"] == 2
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)

    persona_events = [
        r
        for r in store._rows  # type: ignore[attr-defined]
        if r.get("event_type") == EventType.PERSONA_SHELF_UPDATED.value
    ]
    assert len(persona_events) == 1
    ev = persona_events[0]
    assert ev["payload"]["persona_id"] == "commerce"
    assert ev["payload"]["prev_version"] == 1
    assert ev["payload"]["next_version"] == 2
    assert ev["payload"]["fields_changed"] == ["instructions"]
    assert ev["payload"]["actor"] == "alice"


def test_openapi_info_description_present(client: TestClient) -> None:
    spec = client.app.openapi()
    desc = spec.get("info", {}).get("description", "")
    assert isinstance(desc, str) and len(desc.strip()) > 0
    assert "RFC 5988" in desc


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


def test_create_run_and_timeline(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    t = client.get(f"/v1/runs/{run_id}/timeline")
    assert t.status_code == 200
    body = t.json()
    assert len(body["events"]) == 1
    assert "integrator_gate" in body
    assert body["integrator_gate"] is None
    assert body.get("integrator_gate_history") is None
    assert body.get("integrator_gate_delta") is None
    assert "agent_evaluator" in body
    assert body["agent_evaluator"] is None
    assert "self_refinement" in body
    assert body["self_refinement"] is None
    assert "run_escalated" in body
    assert body["run_escalated"] is None
    assert body.get("run_escalated_history") is None
    assert body.get("run_escalated_delta") is None
    assert "security_scan_on_verify" in body
    assert body["security_scan_on_verify"] is None
    assert body.get("security_scan_on_verify_history") is None
    assert body.get("self_refinement_marker_history") is None
    assert "scraper_fetch" in body
    assert body["scraper_fetch"] is None
    assert "universal_critique" in body
    assert body["universal_critique"] is None
    assert "stage_graph" in body
    sg = body.get("stage_graph")
    assert isinstance(sg, dict)
    assert sg.get("stage_count", 0) >= 1
    assert "persona_assignment" in body
    assert body["persona_assignment"] is None


def test_timeline_integrator_gate_summary_from_bundle_gate_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "bundle_title": "Admin RBAC starter",
                "integrator_score": 0.9,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": ["auth-rbac-starter"],
                "integrator_bundle_tags": ["auth"],
                "integrator_matched_tags": ["auth"],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ig = tl["integrator_gate"]
    assert ig is not None
    assert ig["event_id"] == str(eid)
    assert ig["stage_name"] == "bundle_compatibility"
    assert ig["verdict"] == "PASS"
    assert ig["failure_reason_code"] is None
    assert ig["bundle_id"] == "auth-rbac-starter"
    assert ig["integrator_score"] == pytest.approx(0.9)


def test_timeline_integrator_gate_bundle_compatibility_ranking(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    ranking = [
        {"bundle_id": "top", "score": 0.95, "passes_gate": True, "title": "Top"},
        {"bundle_id": "auth-rbac-starter", "score": 0.9, "passes_gate": True},
    ]
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "integrator_score": 0.9,
                "bundle_compatibility_ranking": ranking,
                "bundle_compatibility_ranking_count": 2,
                "selected_bundle_rank": 1,
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    ig = client.get(f"/v1/runs/{run_id}/timeline").json()["integrator_gate"]
    assert ig["bundle_compatibility_ranking_count"] == 2
    assert ig["selected_bundle_rank"] == 1
    assert ig["selected_bundle_id"] == "auth-rbac-starter"
    assert len(ig["bundle_compatibility_ranking"]) == 2


def test_timeline_integrator_gate_excludes_optional_ranking_fields_without_ranking_metadata(
    client: TestClient,
) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "integrator_score": 0.9,
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    ig = client.get(f"/v1/runs/{run_id}/timeline").json()["integrator_gate"]
    assert ig["event_id"] == str(eid)
    assert "bundle_compatibility_ranking" not in ig
    assert "bundle_compatibility_ranking_count" not in ig
    assert "selected_bundle_rank" not in ig
    assert "selected_bundle_id" not in ig


def test_timeline_agent_evaluator_llm_policy_fields(client: TestClient) -> None:
    from agent_core.models import StageStartedEvent, StageStartedPayload

    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    client.app.state.store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "evaluation": {"status": "ok", "gaps": []},
                    "evaluation_branch": "rules_with_llm_policy",
                    "llm_evaluation": {
                        "status": "needs_work",
                        "summary": "policy suggests more coverage",
                        "policy_score": 0.875,
                        "policy_score_band": "meets_threshold",
                    },
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:commerce", attempt=1),
        ),
    )
    ae = client.get(f"/v1/runs/{run_id}/timeline").json()["agent_evaluator"]
    assert ae["evaluation_branch"] == "rules_with_llm_policy"
    assert ae["evaluation_status"] == "ok"
    assert ae["llm_evaluation_summary"] == "policy suggests more coverage"
    assert ae["llm_evaluation_status"] == "needs_work"
    assert ae["llm_evaluation_score"] == 0.875
    assert ae["llm_evaluation_score_band"] == "meets_threshold"


def test_timeline_integrator_gate_history_lists_chronological_gates(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid1 = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid1,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "b-first",
                "bundle_title": "First",
                "integrator_score": 0.5,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": [],
                "integrator_bundle_tags": [],
                "integrator_matched_tags": [],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    eid2 = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid2,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "b-second",
                "bundle_title": "Second",
                "integrator_score": 0.9,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": [],
                "integrator_bundle_tags": [],
                "integrator_matched_tags": [],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.FAIL,
                unanimous_pass_required=False,
                failure_reason_code="integrator_below_threshold",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl["integrator_gate_history"]
    assert isinstance(hist, list) and len(hist) == 2
    assert hist[0]["bundle_id"] == "b-first"
    assert hist[0]["verdict"] == "PASS"
    assert hist[1]["bundle_id"] == "b-second"
    assert hist[1]["verdict"] == "FAIL"
    assert tl["integrator_gate"]["event_id"] == str(eid2)
    assert tl["integrator_gate"]["verdict"] == "FAIL"
    d = tl.get("integrator_gate_delta")
    assert d is not None
    assert d["integrator_score_delta"] == pytest.approx(0.4)
    assert d["verdict_changed"] is True
    assert d["bundle_id_changed"] is True
    assert d["previous_event_id"] == str(eid1)
    assert d["current_event_id"] == str(eid2)


def test_timeline_agent_evaluator_summary_from_stage_started_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="agent_eval:default", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    assert ae["event_id"] == str(eid_first)
    assert ae["stage_name"] == "agent_eval:default"
    assert ae["persona_id"] == "default"
    assert ae["attempt"] == 1

    eid_second = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="agent_eval:backend_engineer", attempt=1),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae2 = tl2["agent_evaluator"]
    assert ae2 is not None
    assert ae2["event_id"] == str(eid_second)
    assert ae2["stage_name"] == "agent_eval:backend_engineer"
    assert ae2["persona_id"] == "backend_engineer"


def test_timeline_agent_evaluator_includes_auto_create_persona_metadata(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "auto_create_persona": {
                        "auto_create_persona_applied": True,
                        "shelf": "business_area",
                        "persona_id": "timeline_ae",
                    },
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:timeline_ae", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    ac = ae.get("auto_create_persona")
    assert isinstance(ac, dict)
    assert ac.get("auto_create_persona_applied") is True


def test_timeline_agent_evaluator_includes_auto_promote_metadata(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:commerce", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    assert ae["event_id"] == str(eid)
    assert ae["persona_id"] == "commerce"
    ap = ae.get("auto_promote")
    assert isinstance(ap, dict)
    assert ap.get("reason") == "env_kill_switch"
    assert ap.get("auto_promote_probation_applied") is False
    assert ae.get("auto_promote_requested") is True
    assert ae.get("auto_promote_applied") is False
    assert ae.get("auto_promote_reason") == "env_kill_switch"


def test_timeline_self_refinement_summary_from_stage_started_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "self_refinement": {
                    "version": "v1",
                    "description": "first pass",
                    "llm_critique": {"summary": "llm says hold"},
                },
            },
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr = tl["self_refinement"]
    assert sr is not None
    assert sr["event_id"] == str(eid_first)
    assert sr["stage_name"] == "self_refinement:policy"
    assert sr["attempt"] == 1
    assert sr["version"] == "v1"
    assert sr["description"] == "first pass"
    assert sr["llm_critique_summary"] == "llm says hold"
    assert sr["marker_count"] == 1
    assert sr["first_marker_occurred_at"] == sr["occurred_at"]
    assert sr["last_marker_occurred_at"] == sr["occurred_at"]
    assert "max_iterations_exceeded" not in sr

    eid_second = uuid4()
    first_occ = sr["occurred_at"]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "self_refinement": {
                    "version": "v2",
                    "description": "second wins",
                },
            },
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr2 = tl2["self_refinement"]
    assert sr2 is not None
    assert sr2["event_id"] == str(eid_second)
    assert sr2["version"] == "v2"
    assert sr2["description"] == "second wins"
    assert sr2["marker_count"] == 2
    assert sr2["first_marker_occurred_at"] == first_occ
    assert sr2["last_marker_occurred_at"] == sr2["occurred_at"]


def test_timeline_self_refinement_phase_d_signal_from_event(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        SelfRefinementLoopSignalledEvent(
            event_type=EventType.SELF_REFINEMENT_LOOP_SIGNALLED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=SelfRefinementLoopSignalledPayload(
                attempt=1,
                max_iterations=3,
            ),
        ),
    )
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"self_refinement": {"version": "v1", "description": "first pass"}},
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr = tl["self_refinement"]
    assert isinstance(sr, dict)
    phase_d = sr.get("phase_d_signal")
    assert isinstance(phase_d, dict)
    assert phase_d.get("signal") == "phase_d_kickoff"
    assert phase_d.get("gate_decision") == "hold"
    assert phase_d.get("loops_remaining") == 0
    assert phase_d.get("orchestration_branch") == "rules"


def test_timeline_self_refinement_llm_critique_stage_from_gate(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="self_refinement.critique",
                verdict=Verdict.PASS,
                unanimous_pass_required=True,
            ),
        ),
    )
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"self_refinement": {"version": "v1"}},
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    sr = client.get(f"/v1/runs/{run_id}/timeline").json()["self_refinement"]
    assert isinstance(sr, dict)
    panel = sr.get("llm_critique_stage")
    assert isinstance(panel, dict)
    assert panel.get("stage_name") == "self_refinement.critique"
    assert panel.get("verdict") == "PASS"


def test_timeline_self_refinement_marker_history(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    for i, ver in enumerate(("v1", "v2", "v3"), start=1):
        store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"self_refinement": {"version": ver}},
                payload=StageStartedPayload(
                    stage_name="self_refinement:policy",
                    attempt=i,
                ),
            ),
        )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl["self_refinement_marker_history"]
    assert hist is not None
    assert len(hist) == 3
    assert [h["version"] for h in hist] == ["v1", "v2", "v3"]
    assert tl["self_refinement"]["marker_count"] == 3


def test_timeline_scraper_fetch_summary_from_stage_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["scraper_fetch"] is None

    eid_pass = uuid4()
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=eid_pass,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "scraper_fetch": {
                    "fetches": [
                        {"url_host": "example.com", "bytes": 100, "http_status": 200},
                        {"url_host": "other.com", "bytes": 50, "http_status": 200},
                    ],
                },
            },
            payload=StagePassedPayload(stage_name="scraper:fetch", duration_ms=12),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sf = tl["scraper_fetch"]
    assert sf is not None
    assert sf["event_id"] == str(eid_pass)
    assert sf["outcome"] == "passed"
    assert sf["fetch_count"] == 2
    assert sf["total_bytes"] == 150
    assert sf.get("reason_code") is None
    fetches = sf.get("fetches")
    assert isinstance(fetches, list)
    assert len(fetches) == 2
    assert fetches[0]["url_host"] == "example.com"
    assert fetches[0]["bytes"] == 100

    eid_fail = uuid4()
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=eid_fail,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "scraper_fetch": {
                    "fetches": [{"url_host": "a.com", "bytes": 10}],
                    "failed_url_host": "b.com",
                },
            },
            payload=StageFailedPayload(
                stage_name="scraper:fetch",
                reason_code="scraper_budget_exceeded",
                message="no bytes remaining",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    sf2 = tl2["scraper_fetch"]
    assert sf2 is not None
    assert sf2["event_id"] == str(eid_fail)
    assert sf2["outcome"] == "failed"
    assert sf2["reason_code"] == "scraper_budget_exceeded"
    assert sf2["fetch_count"] == 1
    assert sf2["total_bytes"] == 10
    assert sf2["failed_url_host"] == "b.com"


def test_timeline_universal_critique_summary_from_gate_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["universal_critique"] is None

    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="planner.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="critique_fail",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc = tl["universal_critique"]
    assert uc is not None
    assert uc["stage_count"] == 2
    assert uc["fail_count"] == 1
    assert uc["pass_count"] == 1
    assert uc["fail_rate"] == 0.5
    assert uc["distinct_fail_stages"] == ["implementation.critique"]
    stages = uc["stages"]
    assert len(stages) == 2
    assert stages[0]["stage_name"] == "planner.critique"
    assert stages[1]["stage_name"] == "implementation.critique"
    assert stages[1]["verdict"] == "FAIL"

    eid_tw = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid_tw,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="test_writer.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc2 = tl2["universal_critique"]
    assert uc2["stage_count"] == 3
    assert uc2["pass_count"] == 2
    by_name = {s["stage_name"]: s for s in uc2["stages"]}
    assert by_name["test_writer.critique"]["event_id"] == str(eid_tw)
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="frontend_writer.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="module_integrator.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl3 = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc3 = tl3["universal_critique"]
    assert uc3["stage_count"] == 5
    assert uc3["pass_count"] == 4
    assert uc3["distinct_fail_stages"] == ["implementation.critique"]
    assert [s["stage_name"] for s in uc3["stages"]] == [
        "planner.critique",
        "implementation.critique",
        "test_writer.critique",
        "frontend_writer.critique",
        "module_integrator.critique",
    ]


def test_timeline_universal_critique_ignores_integrator_gate(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"integrator_gate": True, "bundle_id": "b1"},
            payload=GateDecisionEmittedPayload(
                stage_name="integrator",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl["universal_critique"] is None
    assert tl["integrator_gate"] is not None


def test_timeline_scraper_fetch_ignores_non_scraper_stages(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=StagePassedPayload(stage_name="plan", duration_ms=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl["scraper_fetch"] is None


def test_timeline_run_escalated_summary_from_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="human",
                reason_code="THRESHOLD",
                policy_snapshot_id="snap-1",
                notes="first escalation",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    esc = tl["run_escalated"]
    assert esc is not None
    assert esc["event_id"] == str(eid_first)
    assert esc["actor_id"] == "human"
    assert esc["reason_code"] == "THRESHOLD"
    assert esc["policy_snapshot_id"] == "snap-1"
    assert esc["notes"] == "first escalation"

    eid_second = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system",
                reason_code="ANTI_DEADLOCK",
                policy_snapshot_id=None,
                notes="second wins",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    esc2 = tl2["run_escalated"]
    assert esc2 is not None
    assert esc2["event_id"] == str(eid_second)
    assert esc2["reason_code"] == "ANTI_DEADLOCK"
    assert esc2["notes"] == "second wins"
    assert esc2["actor_id"] == "system"


def test_timeline_run_escalated_history_and_delta(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="human",
                reason_code="THRESHOLD",
                policy_snapshot_id="snap-1",
                notes="first",
            ),
        ),
    )
    tl_one = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl_one["run_escalated_history"] is not None
    assert len(tl_one["run_escalated_history"]) == 1
    assert tl_one["run_escalated_delta"] is None

    eid_second = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system",
                reason_code="ANTI_DEADLOCK",
                policy_snapshot_id=None,
                notes="second",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl2["run_escalated_history"]
    assert hist is not None
    assert len(hist) == 2
    assert hist[0]["reason_code"] == "THRESHOLD"
    assert hist[1]["reason_code"] == "ANTI_DEADLOCK"
    assert tl2["run_escalated"]["event_id"] == str(eid_second)
    delta = tl2["run_escalated_delta"]
    assert delta is not None
    assert delta["reason_code_changed"] is True
    assert delta["previous_reason_code"] == "THRESHOLD"
    assert delta["current_reason_code"] == "ANTI_DEADLOCK"
    assert delta["actor_id_changed"] is True


_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def test_timeline_security_scan_on_verify_summary_from_finding_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    fid_plain = uuid4()
    eid_plain = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_plain,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=FindingCreatedPayload(
                finding_id=fid_plain,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["no scan"],
                required_fixes=[],
            ),
        ),
    )
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["security_scan_on_verify"] is None

    fid_first = uuid4()
    eid_first = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_scan_exit": 0,
                "security_scan_ruff_exit": 0,
                "security_scan_bandit_exit": 0,
                "security_scan_snippet": "bandit ok\n",
            },
            payload=FindingCreatedPayload(
                finding_id=fid_first,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["fail"],
                required_fixes=[],
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ss = tl["security_scan_on_verify"]
    assert ss is not None
    assert ss["event_id"] == str(eid_first)
    assert ss["finding_id"] == str(fid_first)
    assert ss["category"] == "verify"
    assert ss["security_scan_exit"] == 0
    assert ss["security_scan_ruff_exit"] == 0
    assert ss["security_scan_bandit_exit"] == 0
    assert ss["security_scan_snippet"] == "bandit ok\n"

    fid_second = uuid4()
    eid_second = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_scan_exit": 1,
                "security_scan_ruff_exit": 2,
                "security_scan_bandit_exit": 0,
                "security_scan_snippet": "second wins",
            },
            payload=FindingCreatedPayload(
                finding_id=fid_second,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["fail2"],
                required_fixes=[],
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    ss2 = tl2["security_scan_on_verify"]
    assert ss2 is not None
    assert ss2["event_id"] == str(eid_second)
    assert ss2["finding_id"] == str(fid_second)
    assert ss2["security_scan_exit"] == 1
    assert ss2["security_scan_ruff_exit"] == 2
    assert ss2["security_scan_bandit_exit"] == 0
    assert ss2["security_scan_snippet"] == "second wins"
    hist = tl2["security_scan_on_verify_history"]
    assert hist is not None
    assert len(hist) == 2
    assert hist[0]["event_id"] == str(eid_first)
    assert hist[1]["event_id"] == str(eid_second)
    assert hist[1]["security_scan_exit"] == 1


def test_timeline_preflight_summary_from_passed_event(client: TestClient) -> None:
    """fo124: ``GET /v1/runs/{id}/timeline`` exposes a top-level ``preflight`` summary.

    Three assertions:

    * Run without ``model.preflight.passed`` ⇒ ``preflight is None``.
    * After appending a multisample passed event, the projection includes the
      new ``health_latency_samples_ms`` list intact.
    * A second passed event wins (matches the ``latest wins`` convention used
      by the sibling timeline-summary helpers).
    """
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store

    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["preflight"] is None

    eid_first = uuid4()
    store.append(
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="llama3.1:8b",
                context_tokens=8192,
                p95_latency_ms=135,
                checks_passed=[
                    "runtime_reachable",
                    "model_available",
                    "health_latency_measured",
                    "health_latency_multisample",
                    "context_budget_ok",
                ],
                preflight_latency_sample_count=3,
                p95_latency_source="max(health_p95_ms,show_latency_ms,optional_json_probe)",
                health_latency_samples_ms=[120, 130, 135],
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    pf = tl["preflight"]
    assert pf is not None
    assert pf["event_id"] == str(eid_first)
    assert pf["provider"] == "ollama"
    assert pf["validated_model_id"] == "llama3.1:8b"
    assert pf["context_tokens"] == 8192
    assert pf["p95_latency_ms"] == 135
    assert pf["preflight_latency_sample_count"] == 3
    assert pf["health_latency_samples_ms"] == [120, 130, 135]
    assert "health_latency_multisample" in pf["checks_passed"]

    eid_second = uuid4()
    store.append(
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="qwen2.5-coder:14b",
                context_tokens=16384,
                p95_latency_ms=200,
                preflight_latency_sample_count=5,
                health_latency_samples_ms=[180, 190, 200, 210, 220],
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    pf2 = tl2["preflight"]
    assert pf2 is not None
    assert pf2["event_id"] == str(eid_second)
    assert pf2["validated_model_id"] == "qwen2.5-coder:14b"
    assert pf2["health_latency_samples_ms"] == [180, 190, 200, 210, 220]


def test_create_run_invalid_idempotency_key_422(client: TestClient) -> None:
    r = client.post(
        "/v1/runs",
        json={"workflow_profile": "default"},
        headers={"Idempotency-Key": "not-a-uuid"},
    )
    assert r.status_code == 422
    assert r.json().get("code") == "invalid_request"


def test_idempotency_returns_same_run(client: TestClient) -> None:
    key = str(uuid4())
    r1 = client.post(
        "/v1/runs",
        json={"workflow_profile": "default"},
        headers={"Idempotency-Key": key},
    )
    r2 = client.post(
        "/v1/runs",
        json={"workflow_profile": "default"},
        headers={"Idempotency-Key": key},
    )
    run_id = r1.json()["run_id"]
    assert run_id == r2.json()["run_id"]
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert len(tl["events"]) == 1


def test_create_run_accepts_scraper_artifacts_on_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "scraper_artifacts_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_agent_evaluator_on_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "agent_evaluator_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_security_scan_metadata_on_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "security_scan_metadata_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_integrator_gate_mismatch_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "integrator_gate_mismatch"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_escalation_suppress_on_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "escalation_suppress_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_stub_on_profile(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "universal_critique_stub_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_stage_failed_on_profile(
    client: TestClient,
) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "universal_critique_stage_failed_on"})
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_emit_finding_on_gate_fail_profile(
    client: TestClient,
) -> None:
    r = client.post(
        "/v1/runs",
        json={"workflow_profile": "universal_critique_emit_finding_on_gate_fail"},
    )
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_hard_block_on_profile(
    client: TestClient,
) -> None:
    r = client.post(
        "/v1/runs",
        json={"workflow_profile": "universal_critique_hard_block_on"},
    )
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_hard_block_chain_on_profile(
    client: TestClient,
) -> None:
    r = client.post(
        "/v1/runs",
        json={"workflow_profile": "universal_critique_hard_block_chain_on"},
    )
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_create_run_accepts_universal_critique_tw_hard_block_chain_on_profile(
    client: TestClient,
) -> None:
    r = client.post(
        "/v1/runs",
        json={"workflow_profile": "universal_critique_tw_hard_block_chain_on"},
    )
    assert r.status_code == 200
    assert "run_id" in r.json()


def test_unknown_workflow_profile_422(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "does-not-exist-xyz"})
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "workflow_not_found"
    assert "message" in body


def test_post_runs_openapi_documents_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/runs", {})
        .get("post", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    ex = (
        ok.get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex.get("run_id") == "11111111-1111-4111-8111-111111111111"


def test_list_runs_openapi_documents_link_header(client: TestClient) -> None:
    spec = client.app.openapi()
    link_hdr = (
        spec.get("paths", {})
        .get("/v1/runs", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
        .get("headers", {})
        .get("Link")
    )
    assert isinstance(link_hdr, dict)
    assert "schema" in link_hdr


def test_list_runs_ok(client: TestClient) -> None:
    client.post("/v1/runs", json={"workflow_profile": "default"})
    r = client.get("/v1/runs")
    assert r.status_code == 200
    data = r.json()
    assert "run_ids" in data
    assert data.get("total", 0) >= 1
    assert "has_more" in data
    assert data.get("include_summary") == 0
    assert "summaries" not in data


def test_list_runs_created_after_filter(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get(
        "/v1/runs",
        params={"created_after": "2020-01-01T00:00:00Z", "limit": 50},
    )
    assert r.status_code == 200
    assert rid in r.json()["run_ids"]


def test_list_runs_invalid_created_after_returns_problem(client: TestClient) -> None:
    r = client.get(
        "/v1/runs",
        params={"created_after": "not-a-datetime", "limit": 50},
    )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "invalid_request"
    assert "created_after" in body.get("message", "")
    assert body.get("details", {}).get("field") == "created_after_or_created_before"


def test_list_runs_workflow_filter(client: TestClient) -> None:
    a = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get("/v1/runs", params={"workflow_profile": "default", "limit": 50})
    assert r.status_code == 200
    data = r.json()
    assert a in data["run_ids"]
    assert data.get("workflow_profile") == "default"


def test_list_runs_workflow_profile_prefix(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get("/v1/runs", params={"workflow_profile_prefix": "def", "limit": 50})
    assert r.status_code == 200
    assert rid in r.json()["run_ids"]


def test_list_runs_order_oldest_first(client: TestClient) -> None:
    from datetime import datetime, timedelta, timezone

    window_start = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    first = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    second = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get(
        "/v1/runs",
        params={
            "workflow_profile": "default",
            "created_after": window_start,
            "order": "oldest_first",
            "limit": 50,
        },
    )
    assert r.status_code == 200
    ids = r.json()["run_ids"]
    assert first in ids and second in ids
    assert ids.index(first) < ids.index(second)


def test_list_runs_include_summary_returns_summaries(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get("/v1/runs", params={"include_summary": 1, "limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert data.get("include_summary") == 1
    assert "summaries" in data
    assert rid in data["summaries"]
    assert "event_count" in data["summaries"][rid]


def test_list_runs_include_summary_limit_exceeded_422(client: TestClient) -> None:
    r = client.get("/v1/runs", params={"include_summary": 1, "limit": 50})
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "include_summary_limit_exceeded"


def test_list_runs_has_escalation_filter(client: TestClient) -> None:
    plain = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    escalated = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    esc = client.post(
        f"/v1/runs/{escalated}/actions/escalate",
        json={"actor_id": "test", "reason_code": "manual"},
    )
    assert esc.status_code == 200

    r_all = client.get("/v1/runs", params={"workflow_profile": "default", "limit": 100})
    assert r_all.status_code == 200
    assert plain in r_all.json()["run_ids"]
    assert escalated in r_all.json()["run_ids"]
    assert "has_escalation" not in r_all.json()

    r_yes = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "has_escalation": 1, "limit": 100},
    )
    assert r_yes.status_code == 200
    data_yes = r_yes.json()
    assert data_yes.get("has_escalation") == 1
    assert escalated in data_yes["run_ids"]
    assert plain not in data_yes["run_ids"]

    r_no = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "has_escalation": 0, "limit": 100},
    )
    assert r_no.status_code == 200
    data_no = r_no.json()
    assert data_no.get("has_escalation") == 0
    assert plain in data_no["run_ids"]
    assert escalated not in data_no["run_ids"]


def test_list_runs_link_header_preserves_has_escalation(client: TestClient) -> None:
    for _ in range(3):
        client.post("/v1/runs", json={"workflow_profile": "default"})
    r = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "limit": 1, "offset": 0, "has_escalation": 0},
    )
    assert r.status_code == 200
    link = r.headers.get("link")
    assert link is not None
    assert "has_escalation=0" in link


def test_list_runs_link_header_next_and_prev(client: TestClient) -> None:
    for _ in range(3):
        client.post("/v1/runs", json={"workflow_profile": "default"})
    r = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "limit": 2, "offset": 0, "order": "newest_first"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["has_more"] is True
    link = r.headers.get("link")
    assert link is not None
    assert 'rel="next"' in link
    assert "offset=2" in link
    assert "limit=2" in link

    r2 = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "limit": 2, "offset": 2, "order": "newest_first"},
    )
    assert r2.status_code == 200
    link2 = r2.headers.get("link")
    assert link2 is not None
    assert 'rel="prev"' in link2
    assert "offset=0" in link2


def test_list_runs_no_link_when_last_page_covers_total(client: TestClient) -> None:
    from datetime import datetime, timedelta, timezone

    window_start = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    client.post("/v1/runs", json={"workflow_profile": "default"})
    r0 = client.get(
        "/v1/runs",
        params={
            "workflow_profile": "default",
            "created_after": window_start,
            "limit": 1,
            "offset": 0,
        },
    )
    assert r0.status_code == 200
    total = r0.json()["total"]
    assert total >= 1
    r = client.get(
        "/v1/runs",
        params={
            "workflow_profile": "default",
            "created_after": window_start,
            "limit": total,
            "offset": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["has_more"] is False
    assert r.headers.get("link") is None


def test_list_runs_keyset_cursor_walk(client: TestClient) -> None:
    client.post("/v1/runs", json={"workflow_profile": "default"})
    client.post("/v1/runs", json={"workflow_profile": "default"})
    r0 = client.get(
        "/v1/runs",
        params={"workflow_profile": "default", "limit": 1, "offset": 0, "order": "newest_first"},
    )
    assert r0.status_code == 200
    d0 = r0.json()
    assert len(d0["run_ids"]) == 1
    nc0 = d0.get("next_cursor")
    assert d0["has_more"] is True
    assert isinstance(nc0, str) and nc0
    link0 = r0.headers.get("link") or ""
    assert "offset=1" in link0

    r1 = client.get(
        "/v1/runs",
        params={
            "workflow_profile": "default",
            "limit": 1,
            "offset": 0,
            "order": "newest_first",
            "cursor": nc0,
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["run_ids"]) == 1
    assert d1["run_ids"][0] != d0["run_ids"][0]
    assert d1["offset"] == 0
    if d1.get("has_more"):
        link1 = r1.headers.get("link") or ""
        assert "cursor=" in link1


def test_list_runs_cursor_with_nonzero_offset_422(client: TestClient) -> None:
    client.post("/v1/runs", json={"workflow_profile": "default"})
    client.post("/v1/runs", json={"workflow_profile": "default"})
    nc = client.get("/v1/runs", params={"limit": 1, "offset": 0}).json()["next_cursor"]
    assert nc
    r = client.get("/v1/runs", params={"cursor": nc, "offset": 1, "limit": 1})
    assert r.status_code == 422
    assert r.json().get("code") == "invalid_request"


def test_list_runs_invalid_cursor_422(client: TestClient) -> None:
    r = client.get("/v1/runs", params={"cursor": "not-valid-base64!!!", "limit": 5})
    assert r.status_code == 422
    assert r.json().get("code") == "invalid_cursor"


def test_list_runs_invalid_status_422(client: TestClient) -> None:
    r = client.get("/v1/runs", params={"status": "bogus", "limit": 5})
    assert r.status_code == 422
    assert r.json().get("code") == "invalid_request"


def test_list_runs_status_created_excludes_running(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r_all = client.get("/v1/runs", params={"limit": 100})
    assert rid in r_all.json()["run_ids"]
    r_created = client.get("/v1/runs", params={"status": "created", "limit": 100})
    assert r_created.status_code == 200
    assert rid in r_created.json()["run_ids"]
    r_terminal = client.get("/v1/runs", params={"status": "terminal", "limit": 100})
    assert r_terminal.status_code == 200
    assert rid not in r_terminal.json()["run_ids"]


def test_actions_retry_invalid_run_id_path_422(client: TestClient) -> None:
    r = client.post("/v1/runs/not-a-uuid/actions/retry")
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "validation_error"


def test_timeline_404_problem_envelope(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(f"/v1/runs/{rid}/timeline")
    assert r.status_code == 404
    body = r.json()
    assert body.get("code") == "run_not_found"


def test_execute_role_requires_admin_token(client: TestClient) -> None:
    r = client.post("/v1/roles/00000000-0000-4000-8000-000000000001/execute")
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "unauthorized"
    assert "message" in body
    ok = client.post(
        "/v1/roles/00000000-0000-4000-8000-000000000001/execute",
        headers={"X-Hermes-Admin-Token": "test-admin-token"},
    )
    assert ok.status_code == 200


def test_lifecycle_start_and_plan(client: TestClient) -> None:
    run_id = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    s = client.post(f"/v1/runs/{run_id}/lifecycle/start")
    assert s.status_code == 200
    p = client.post(f"/v1/runs/{run_id}/lifecycle/plan")
    assert p.status_code == 200
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    types = [e["event_type"] for e in tl["events"]]
    assert "run.created" in types
    assert "model.preflight.passed" in types
    assert "critic.verdict.emitted" in types


def test_create_run_rejects_invalid_stage_graph(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "stage_graph_invalid_cycle"})
    assert r.status_code == 422
    assert r.json().get("code") in ("validation_error", "invalid_request")


def test_timeline_includes_stage_graph_summary(client: TestClient) -> None:
    run_id = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sg = tl.get("stage_graph")
    assert isinstance(sg, dict)
    assert sg.get("stage_count", 0) >= 5
    assert sg.get("parallel_group_count", 0) >= 1
    assert "plan" in (sg.get("ordered_stage_names") or [])


def test_timeline_parallel_writer_groups_after_writer_pass(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    with patch.dict(os.environ, {"HERMES_STUB_IMPLEMENTATION_CRITICS": "1"}, clear=False):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            ex = client.post(f"/v1/runs/{run_id}/lifecycle/verify")
            assert ex.status_code == 200
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    groups = tl.get("parallel_writer_groups")
    assert isinstance(groups, list)
    assert groups[0]["group_id"] == "writers"
    assert "implementation" in groups[0]["stages"]
    assert groups[0].get("dispatch_mode") == "sequential"


def test_timeline_parallel_dispatch_mode_when_enabled(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post(
        "/v1/runs",
        json={"workflow_profile": "parallel_writers_on"},
    ).json()["run_id"]
    with patch.dict(os.environ, {"HERMES_PARALLEL_WRITERS": "1"}, clear=False):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            resp = client.post(f"/v1/runs/{run_id}/lifecycle/verify")
            assert resp.status_code == 200
    groups = client.get(f"/v1/runs/{run_id}/timeline").json().get("parallel_writer_groups")
    assert isinstance(groups, list)
    assert groups[0].get("dispatch_mode") == "parallel"
    assert "frontend_writer" in (groups[0].get("stages") or [])


def test_timeline_parallel_stage_details_include_test_writer_failure(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post(
        "/v1/runs",
        json={"workflow_profile": "test_writer_stage_on"},
    ).json()["run_id"]
    with patch.dict(
        os.environ,
        {"HERMES_PARALLEL_WRITERS": "1", "HERMES_TEST_WRITER_STAGE": "1"},
        clear=False,
    ):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            with patch(
                "hermes_orchestrator.pipeline.run_test_writer_stage",
                return_value=(7, "boom", "subprocess"),
            ):
                resp = client.post(f"/v1/runs/{run_id}/lifecycle/verify")
                assert resp.status_code == 200
    groups = client.get(f"/v1/runs/{run_id}/timeline").json().get("parallel_writer_groups")
    assert isinstance(groups, list)
    details = groups[0].get("stage_details") or []
    tw = next(d for d in details if d.get("stage_name") == "test_writer")
    assert tw.get("exit_code") == 7
    assert tw.get("failure_reason") == "test_writer_stage_failed"
    assert tw.get("body_mode") == "subprocess"


def test_timeline_parallel_stage_details_include_test_writer_body_mode_stub(
    client: TestClient,
) -> None:
    from unittest.mock import patch

    run_id = client.post(
        "/v1/runs",
        json={"workflow_profile": "parallel_writers_on"},
    ).json()["run_id"]
    with patch.dict(
        os.environ,
        {
            "HERMES_PARALLEL_WRITERS": "1",
            "HERMES_TEST_WRITER_STAGE": "1",
            "HERMES_TEST_WRITER_LLM_BODY": "1",
            "HERMES_TEST_WRITER_LLM_STUB": "1",
            "HERMES_USE_LLM": "1",
        },
        clear=False,
    ):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            resp = client.post(f"/v1/runs/{run_id}/lifecycle/verify")
            assert resp.status_code == 200
    groups = client.get(f"/v1/runs/{run_id}/timeline").json().get("parallel_writer_groups")
    assert isinstance(groups, list)
    details = groups[0].get("stage_details") or []
    tw = next(d for d in details if d.get("stage_name") == "test_writer")
    assert tw.get("body_mode") == "stub"


def test_lifecycle_verify_returns_dispatch_queued(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    with patch.dict(os.environ, {"HERMES_RUN_DISPATCH": "memory"}, clear=False):
        resp = client.post(f"/v1/runs/{run_id}/lifecycle/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("dispatch") == "queued"


def test_timeline_agent_evaluator_coverage_gate(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post(
        "/v1/runs",
        json={"workflow_profile": "agent_evaluator_default_on"},
    ).json()["run_id"]
    with patch.dict(os.environ, {"HERMES_AGENT_EVALUATOR": "1"}, clear=False):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            client.post(f"/v1/runs/{run_id}/lifecycle/verify")
    ae = client.get(f"/v1/runs/{run_id}/timeline").json().get("agent_evaluator")
    assert isinstance(ae, dict)
    assert ae.get("critique_gate_verdict") == "FAIL"


def test_timeline_critic_matrix_live_when_gates_exist(client: TestClient) -> None:
    from unittest.mock import patch

    run_id = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    with patch.dict(os.environ, {"HERMES_STUB_IMPLEMENTATION_CRITICS": "1"}, clear=False):
        with patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ):
            client.post(
                f"/v1/runs/{run_id}/lifecycle/verify",
                headers={"X-Hermes-Admin-Token": "test-admin-token"},
            )
    live = client.get(f"/v1/runs/{run_id}/timeline").json().get("critic_matrix_live")
    assert isinstance(live, dict)
    assert isinstance(live.get("rows"), list)
    assert live["summary"]["pass_count"] >= 1


def test_timeline_universal_critique_effective_from_run_created(client: TestClient) -> None:
    run_id = client.post(
        "/v1/runs",
        json={"workflow_profile": "universal_critique_on"},
    ).json()["run_id"]
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    events = tl["events"]
    rc = next(e for e in events if e["event_type"] == "run.created")
    uce = (rc.get("metadata") or {}).get("universal_critique_effective")
    assert isinstance(uce, dict)
    assert uce.get("default_enabled") is True
    assert uce.get("tw_enabled") is True
    assert isinstance(uce.get("unanimous_gate_enforce"), bool)
