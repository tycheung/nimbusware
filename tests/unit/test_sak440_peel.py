from __future__ import annotations

from unittest.mock import patch

import pytest

from compute.broker_node_match import (
    caps_dict_from_broker_node,
    pick_broker_node_for_user,
    user_id_from_broker_node,
)


def test_pick_broker_node_for_user() -> None:
    nodes = [
        {"label": "other", "caps": ["user:a"]},
        {"label": "user:b", "caps": ["gpu=1"]},
    ]
    hit = pick_broker_node_for_user(nodes, "b")
    assert hit is not None
    assert user_id_from_broker_node(hit) == "b"
    assert caps_dict_from_broker_node(hit).get("gpu") == "1"


def test_inmemory_node_store_refuses_under_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.node_store import InMemoryComputeNodeStore

    with pytest.raises(RuntimeError, match="InMemoryComputeNodeStore unavailable"):
        InMemoryComputeNodeStore()


def test_postgres_node_store_refuses_under_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from compute.node_store import PostgresComputeNodeStore

    with pytest.raises(RuntimeError, match="PostgresComputeNodeStore unavailable"):
        PostgresComputeNodeStore("postgresql://localhost/x")


def test_capacity_fit_reraises_broker_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from pathlib import Path

    from hw.fit import rank_models
    from hw.profile import HardwareProfile

    with patch(
        "broker_client.stage_bind.capacity.capacity_fit_via_broker",
        side_effect=RuntimeError("broker_miss: fit down"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            rank_models(
                Path("."),
                HardwareProfile(tier="medium"),
                binding_id="b1",
                candidates=[{"id": "m1"}],
            )


def test_worker_cli_node_unwrap() -> None:
    from compute.worker_cli import _node_dict_from_broker_raw

    out = _node_dict_from_broker_raw(
        {"node": {"id": "n1", "label": "w"}},
        require_id=True,
    )
    assert out["node_id"] == "n1"


def test_pipeline_enqueue_requires_work_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.broker_session_status import assert_broker_compute_record_ok

    with pytest.raises(RuntimeError, match="missing work"):
        assert_broker_compute_record_ok(
            {"ok": True},
            feature="pipeline_enqueue",
            record_key="work",
        )
    ok = assert_broker_compute_record_ok(
        {"work": {"id": "w1"}, "via": "broker"},
        feature="pipeline_enqueue",
        record_key="work",
    )
    assert ok["work"]["id"] == "w1"
