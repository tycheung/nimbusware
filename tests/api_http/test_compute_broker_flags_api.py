from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.app import app
from compute.work_unit import get_work_unit_queue


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_claim_under_compute_1_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("down"),
    ):
        resp = client.post(
            "/v1/compute/work-units/claim",
            json={"node_id": str(uuid4())},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("work_unit") is None
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_claim_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("down"),
    ):
        resp = client.post(
            "/v1/compute/work-units/claim",
            json={"node_id": str(uuid4())},
        )
    assert resp.status_code == 503
    detail = resp.json().get("detail") or resp.json()
    assert detail.get("code") == "broker_compute_only"


def _assert_compute_2_problem(resp) -> None:
    assert resp.status_code == 503
    detail = resp.json().get("detail") or resp.json()
    assert detail.get("code") == "broker_compute_only"


def test_complete_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: complete hard-refuses local mesh under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    wid = uuid4()
    resp = client.post(
        f"/v1/compute/work-units/{wid}/complete",
        json={"status": "ok", "result": {}},
    )
    _assert_compute_2_problem(resp)


def test_terminate_restart_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: terminate-restart hard-refuses local mesh under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    wid = uuid4()
    resp = client.post(f"/v1/compute/work-units/{wid}/terminate-restart")
    _assert_compute_2_problem(resp)


def test_session_compute_status_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: session compute/status maps broker failure to 503 under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from api.routes import chat_session as cs

    sid = uuid4()
    with (
        patch.object(cs, "session_or_404", return_value=object()),
        patch(
            "compute.broker_session_status.broker_session_compute_status",
            side_effect=RuntimeError("status down"),
        ),
    ):
        with pytest.raises(Exception) as ei:
            cs.session_compute_status(
                session_id=sid,
                chat_store=object(),  # type: ignore[arg-type]
                _user=object(),  # type: ignore[arg-type]
            )
    exc = ei.value
    from fastapi import HTTPException

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 503
    assert exc.detail.get("code") == "broker_compute_only"


def test_session_opt_in_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: session opt-in maps broker failure to 503 under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import chat_session as cs

    sid = uuid4()
    with (
        patch.object(cs, "session_or_404", return_value=object()),
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            side_effect=RuntimeError("register down"),
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            cs.session_compute_opt_in(
                session_id=sid,
                body=cs.SessionComputeOptInBody(enabled=True),
                request=object(),  # type: ignore[arg-type]
                chat_store=object(),  # type: ignore[arg-type]
                user=None,
                _user=object(),  # type: ignore[arg-type]
            )
    assert ei.value.status_code == 503
    assert ei.value.detail.get("code") == "broker_compute_only"


def test_delegate_control_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: delegate-control maps no-node to 503 under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    monkeypatch.setenv("NIMBUSWARE_COLLAB", "1")
    from fastapi import HTTPException

    from api.routes import chat_session as cs

    sid = uuid4()
    mock_user = MagicMock()
    mock_user.user_id = uuid4()
    with (
        patch.object(cs, "session_or_404", return_value=object()),
        patch.object(cs, "require_collab_enabled"),
        patch.object(
            cs,
            "require_session_participant",
        ),
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": []},
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            cs.session_compute_delegate_control(
                session_id=sid,
                body=cs.DelegateControlBody(allow_host_resource_management=True),
                request=object(),  # type: ignore[arg-type]
                chat_store=object(),  # type: ignore[arg-type]
                collab_store=object(),  # type: ignore[arg-type]
                user=mock_user,
                _user=object(),  # type: ignore[arg-type]
            )
    assert ei.value.status_code == 503
    assert ei.value.detail.get("code") == "broker_compute_only"


def test_fleet_mesh_status_under_compute_2_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak490-g: fleet-mesh status maps broker failure to 503 under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes.enterprise import fleet_mesh as fm

    with patch(
        "api.routes.enterprise.fleet_mesh.broker_session_compute_status",
        side_effect=RuntimeError("fleet down"),
    ):
        with pytest.raises(HTTPException) as ei:
            fm.fleet_mesh_status(_gate=object(), session_id=uuid4())  # type: ignore[arg-type]
    assert ei.value.status_code == 503
    assert ei.value.detail.get("code") == "broker_compute_only"


def _assert_handler_compute_2_refuse(exc: BaseException) -> None:
    from fastapi import HTTPException

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 503
    assert exc.detail.get("code") == "broker_compute_only"


def test_enqueue_under_compute_2_broker_down_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-f: enqueue broker-down → 503 broker_compute_only under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import compute as c

    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=RuntimeError("enq down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        c.enqueue_work_unit(
            body=c.WorkUnitEnqueueBody(
                run_id=uuid4(),
                stage_name="implementation",
                payload={},
            ),
            _=object(),  # type: ignore[arg-type]
        )
    _assert_handler_compute_2_refuse(ei.value)


def test_nodes_list_under_compute_2_broker_down_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-f: nodes GET broker-down → 503 broker_compute_only under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import compute as c

    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            side_effect=RuntimeError("nodes down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        c.list_compute_nodes(_=object(), session_id=uuid4())  # type: ignore[arg-type]
    _assert_handler_compute_2_refuse(ei.value)


def test_queue_depth_under_compute_2_broker_down_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-f: queue GET broker-down → 503 broker_compute_only under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import compute as c

    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=RuntimeError("queue down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        c.work_unit_queue_depth(_=object(), session_id=uuid4())  # type: ignore[arg-type]
    _assert_handler_compute_2_refuse(ei.value)


def test_register_under_compute_2_broker_down_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-f: register broker-down → 503 broker_compute_only under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import compute as c

    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            side_effect=RuntimeError("reg down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        c.register_compute_node(
            body=c.ComputeNodeRegisterBody(
                base_url="http://worker.test",
                display_name="w1",
            ),
            _=object(),  # type: ignore[arg-type]
        )
    _assert_handler_compute_2_refuse(ei.value)


def test_heartbeat_under_compute_2_broker_down_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-f: heartbeat broker-down → 503 broker_compute_only under COMPUTE=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from api.routes import compute as c

    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            side_effect=RuntimeError("hb down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        c.heartbeat_compute_node(
            node_id=uuid4(),
            body=c.ComputeNodeHeartbeatBody(),
            _=object(),  # type: ignore[arg-type]
        )
    _assert_handler_compute_2_refuse(ei.value)


def test_enqueue_under_compute_1_broker_hit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"ok": True, "via": "broker", "work": {"id": "w1"}},
    ):
        resp = client.post(
            "/v1/compute/work-units/enqueue",
            json={
                "run_id": str(uuid4()),
                "stage_name": "implementation",
                "agent_role": "backend_writer",
                "payload": {"mesh_assignment": True},
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker"
    assert body.get("work_unit") is not None


def test_nodes_list_error_plus_empty_list_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak438-h: error + nodes=[] must not look like via=broker success."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "nodes down", "nodes": []},
    ):
        resp = client.get(f"/v1/compute/nodes?session_id={uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("status") == "degraded"


def test_register_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak438-h: register error dict → broker_miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "reg down", "node": None},
    ):
        resp = client.post(
            "/v1/compute/nodes/register",
            json={
                "base_url": "http://worker.test",
                "display_name": "w1",
                "host_label": "w1",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert "reg down" in str(body.get("error") or "")


def test_enqueue_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"error": "enq down", "work": None},
    ):
        resp = client.post(
            "/v1/compute/work-units/enqueue",
            json={
                "run_id": str(uuid4()),
                "stage_name": "implementation",
                "payload": {},
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("work_unit") is None


def test_heartbeat_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak439-h: heartbeat error dict → broker_miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    nid = uuid4()
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "hb down", "node": None},
    ):
        resp = client.post(f"/v1/compute/nodes/{nid}/heartbeat", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert "hb down" in str(body.get("error") or "")


def test_terminate_restart_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak439-h: terminate-restart error dict → broker_miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    wid = uuid4()
    with patch(
        "broker_client.stage_bind.compute.terminate_restart_via_broker",
        side_effect=RuntimeError("broker_miss: requeue down"),
    ):
        resp = client.post(f"/v1/compute/work-units/{wid}/terminate-restart")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"


def test_claim_empty_queue_via_broker(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """sak439-h: empty queue poll stays via=broker (not broker_miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"work": None, "error": "queue empty"},
    ):
        resp = client.post(
            "/v1/compute/work-units/claim",
            json={"node_id": str(uuid4())},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker"
    assert body.get("work_unit") is None


def test_openapi_claim_documents_via_schema(client: TestClient) -> None:
    """sak440-g: claim response schema includes via."""
    spec = client.app.openapi()
    claim = spec["paths"]["/v1/compute/work-units/claim"]["post"]
    assert "sak440-g" in claim.get("summary", "")
    schema = claim["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema.get("$ref", "").endswith("WorkUnitClaimResponse")
    props = (
        spec.get("components", {})
        .get("schemas", {})
        .get("WorkUnitClaimResponse", {})
        .get("properties", {})
    )
    assert "via" in props
    assert "work_unit" in props


def test_openapi_nodes_and_queue_document_via(client: TestClient) -> None:
    """sak441-e: nodes list + queue depth schemas include via."""
    spec = client.app.openapi()
    nodes = spec["paths"]["/v1/compute/nodes"]["get"]
    assert "sak441-e" in nodes.get("summary", "")
    assert nodes["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ComputeNodeListResponse"
    )
    queue = spec["paths"]["/v1/compute/work-units/queue"]["get"]
    assert "sak441-e" in queue.get("summary", "")
    assert queue["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "WorkUnitQueueDepthResponse"
    )


def test_openapi_write_routes_document_schemas(client: TestClient) -> None:
    """sak442-e: register/enqueue/complete use named write schemas."""
    spec = client.app.openapi()
    reg = spec["paths"]["/v1/compute/nodes/register"]["post"]
    assert "sak442-e" in reg.get("summary", "")
    assert reg["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ComputeNodeWriteResponse"
    )
    enq = spec["paths"]["/v1/compute/work-units/enqueue"]["post"]
    assert enq["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "WorkUnitWriteResponse"
    )


def test_complete_under_compute_1_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    wid = uuid4()
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("down"),
    ):
        resp = client.post(
            f"/v1/compute/work-units/{wid}/complete",
            json={"status": "ok", "result": {}},
        )
    assert resp.status_code == 200
    assert resp.json().get("via") == "broker_miss"


def test_nodes_list_under_compute_1_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        side_effect=RuntimeError("down"),
    ):
        resp = client.get(f"/v1/compute/nodes?session_id={uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("nodes") == []


def test_nodes_list_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak437-h: broker error dict must not look like via=broker empty success."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "nodes down", "nodes": None},
    ):
        resp = client.get(f"/v1/compute/nodes?session_id={uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("status") == "degraded"
    assert "nodes down" in str(body.get("error") or "")


def test_queue_depth_error_dict_is_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak437-h: queue depth error dict → broker_miss (not silent queued=0 via=broker)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"error": "work down", "work": None},
    ):
        resp = client.get(f"/v1/compute/work-units/queue?session_id={uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("status") == "degraded"
    assert body.get("queued") == 0


def test_fleet_mesh_status_queue_miss_degraded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from api.routes.enterprise import fleet_mesh as fm

    nid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": [{"id": nid, "label": "n1", "caps": []}]},
        ),
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=RuntimeError("work down"),
        ),
        patch.object(fm, "fleet_mesh_status", wraps=fm.fleet_mesh_status),
    ):
        # Call helper directly to avoid enterprise auth gate in TestClient.
        out = fm.fleet_mesh_status(_gate=object(), session_id=uuid4())  # type: ignore[arg-type]
    assert out["status"] == "degraded"
    assert out["via"] == "broker_miss"
    assert out["queue_depth"] == 0
    assert len(out.get("nodes") or []) == 1
    assert out["nodes"][0]["node_id"] == nid
    assert "work down" in str(out.get("error") or "")


def test_session_compute_status_under_compute_1_broker_miss(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak436-h: chat compute/status returns broker_miss + degraded (no silent zeros)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from api.routes import chat_session as cs

    sid = uuid4()
    with (
        patch.object(cs, "session_or_404", return_value=object()),
        patch(
            "compute.broker_session_status.broker_session_compute_status",
            side_effect=RuntimeError("status down"),
        ),
    ):
        out = cs.session_compute_status(
            session_id=sid,
            chat_store=object(),  # type: ignore[arg-type]
            _user=object(),  # type: ignore[arg-type]
        )
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["queue_depth"] == 0
    assert out["nodes"] == []
    assert "status down" in str(out.get("error") or "")


def test_session_compute_status_nodes_ok_queue_fail_degraded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak492-g: session compute/status preserves nodes on queue miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from api.routes import chat_session as cs

    sid = uuid4()
    nid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    with (
        patch.object(cs, "session_or_404", return_value=object()),
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": [{"id": nid, "label": "n1", "caps": []}]},
        ),
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"error": "work down", "work": []},
        ),
    ):
        out = cs.session_compute_status(
            session_id=sid,
            chat_store=object(),  # type: ignore[arg-type]
            _user=object(),  # type: ignore[arg-type]
        )
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["queue_depth"] == 0
    assert len(out.get("nodes") or []) == 1
    assert out["nodes"][0]["node_id"] == nid
    assert "work down" in str(out.get("error") or "")


def test_nodes_list_under_compute_1_feature_tagged(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak436-h: nodes list miss uses shared map (feature tag)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        side_effect=RuntimeError("nodes down"),
    ):
        resp = client.get(f"/v1/compute/nodes?session_id={uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("via") == "broker_miss"
    assert body.get("feature") == "compute_nodes_list"
