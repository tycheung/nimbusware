from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow

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


def test_actions_retry_records_retry_stage(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.post(f"/v1/runs/{rid}/actions/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "retry_recorded"
    types = [e["event_type"] for e in client.get(f"/v1/runs/{rid}/timeline").json()["events"]]
    assert "stage.started" in types


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
        headers={"X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"},
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
                headers={"X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"},
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
