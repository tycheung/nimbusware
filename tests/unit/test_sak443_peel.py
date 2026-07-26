from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from compute.broker_session_status import (
    assert_broker_compute_ok,
    assert_broker_compute_record_ok,
    is_claim_empty_queue_error,
    normalize_claim_work_response,
)


@pytest.mark.parametrize(
    ("raw", "list_key", "ok"),
    [
        ({"nodes": []}, "nodes", True),
        ({"nodes": None}, "nodes", False),
        ({"error": "x", "nodes": []}, "nodes", False),
        ({"work": []}, "work", True),
        ({"work": None}, "work", False),
    ],
)
def test_peel_assert_list_contract(raw: dict, list_key: str, ok: bool) -> None:
    """sak443-e: list assert contract matrix."""
    if ok:
        assert assert_broker_compute_ok(raw, feature="t", list_key=list_key) is raw
    else:
        with pytest.raises(RuntimeError, match="broker_miss"):
            assert_broker_compute_ok(raw, feature="t", list_key=list_key)


def test_peel_assert_record_and_claim_contract() -> None:
    assert (
        assert_broker_compute_record_ok(
            {"work": {"id": "w1"}},
            feature="t",
            record_key="work",
        )["work"]["id"]
        == "w1"
    )
    assert is_claim_empty_queue_error({"work": None, "error": "queue empty"})
    empty = normalize_claim_work_response({"work": None, "error": "no work"})
    assert empty["via"] == "broker"
    with pytest.raises(RuntimeError, match="broker_miss"):
        normalize_claim_work_response({"work": None, "error": "down"})


def test_apply_preset_capacity_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    orch.repo_root = "."
    body = pmr.ApplyPresetBody(model_id="m1", preset="balanced")
    with patch(
        "api.routes.platform_model_routing.get_cached_profile",
        side_effect=RuntimeError("CAPACITY miss"),
    ):
        out = pmr.post_apply_preset(orch, body)
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "platform_models_apply_preset"


def test_claim_no_try_broker_call_soft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from uuid import uuid4

    from api.routes import compute as compute_routes

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("claim down"),
    ):
        out = compute_routes.claim_work_unit(
            compute_routes.WorkUnitClaimBody(node_id=uuid4()),
            _=None,  # type: ignore[arg-type]
        )
    assert out.get("via") == "broker_miss"
    assert out.get("work_unit") is None


def test_capacity_try_capacity_or_refuse_removed() -> None:
    """sak445-a: dead try_broker_call / try_capacity_or_refuse removed from capacity_route."""
    from hw import capacity_route as cr

    assert not hasattr(cr, "try_broker_call")
    assert not hasattr(cr, "try_capacity_or_refuse")
    assert callable(cr.map_broker_capacity_http_miss)
    assert callable(cr.refuse_legacy)


def test_opt_out_via_broker_opt_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from uuid import uuid4

    from fastapi import Request

    from api.routes import chat_session as cs

    session_id = uuid4()
    body = cs.SessionComputeOptInBody(enabled=False)
    chat_store = MagicMock()
    chat_store.get_session.return_value = MagicMock()
    req = MagicMock(spec=Request)
    with patch("api.routes.chat_session.session_or_404"):
        out = cs.session_compute_opt_in(
            session_id,
            body,
            req,
            chat_store,
            user=None,
            _user=None,  # type: ignore[arg-type]
        )
    assert out["via"] == "broker_opt_out"
    assert out["node"] is None
    assert out["feature"] == "session_compute_opt_out"
