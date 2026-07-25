from __future__ import annotations

import pytest

from broker_client import try_broker_compute_work


def test_try_broker_compute_work_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    assert try_broker_compute_work({"kind": "echo"}) is None


def test_try_broker_compute_work_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")

    import broker_client.compute_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "compute_work_via_broker",
        lambda payload, client=None: {"job_id": "j1"},
    )

    out = try_broker_compute_work({"kind": "echo", "input": "hi"})
    assert out == {"job_id": "j1"}


def test_try_broker_compute_work_peel_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak435-a: under COMPUTE=1, bridge re-raises (no None soft miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")

    import broker_client.compute_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "compute_work_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_compute_work({"kind": "echo"})


def test_try_broker_compute_work_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")

    import broker_client.compute_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "compute_work_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_compute_work({"kind": "echo"})
