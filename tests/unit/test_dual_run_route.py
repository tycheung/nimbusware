from __future__ import annotations

import pytest

from broker_client.dual_run_route import try_or_refuse


def test_try_or_refuse_success() -> None:
    assert try_or_refuse(
        lambda: {"ok": True},
        enabled=lambda: True,
        broker_only=lambda: False,
        msg="refuse",
    ) == {"ok": True}


def test_try_or_refuse_peel_off_returns_none() -> None:
    assert (
        try_or_refuse(
            lambda: (_ for _ in ()).throw(ValueError("legacy soft")),
            enabled=lambda: False,
            broker_only=lambda: False,
            msg="refuse",
        )
        is None
    )


def test_try_or_refuse_dual_run_refuses() -> None:
    with pytest.raises(RuntimeError, match="broker_miss: compute") as exc_info:
        try_or_refuse(
            lambda: (_ for _ in ()).throw(ValueError("upstream")),
            enabled=lambda: True,
            broker_only=lambda: False,
            msg="broker_miss: compute",
        )
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "upstream"


def test_try_or_refuse_dual_run_never_returns_none() -> None:
    """Peel on must raise — never soft-return None after bare except."""
    with pytest.raises(RuntimeError):
        try_or_refuse(
            lambda: (_ for _ in ()).throw(OSError("down")),
            enabled=lambda: True,
            broker_only=lambda: False,
            msg="refuse",
        )


def test_try_or_refuse_broker_only_reraises_original() -> None:
    with pytest.raises(ValueError, match="transport down") as exc_info:
        try_or_refuse(
            lambda: (_ for _ in ()).throw(ValueError("transport down")),
            enabled=lambda: True,
            broker_only=lambda: True,
            msg="refuse",
        )
    assert exc_info.type is ValueError
    assert not isinstance(exc_info.value, RuntimeError)


def test_try_or_refuse_broker_only_prefers_original_over_refuse() -> None:
    with pytest.raises(ConnectionError, match="503"):
        try_or_refuse(
            lambda: (_ for _ in ()).throw(ConnectionError("503")),
            enabled=lambda: True,
            broker_only=lambda: True,
            msg="would refuse",
        )


def test_try_or_refuse_with_env_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from broker_client.flags import broker_compute_enabled, broker_compute_only

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with pytest.raises(RuntimeError, match="env refuse"):
        try_or_refuse(
            lambda: (_ for _ in ()).throw(RuntimeError("inner")),
            enabled=broker_compute_enabled,
            broker_only=broker_compute_only,
            msg="env refuse",
        )

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    with pytest.raises(RuntimeError, match="inner"):
        try_or_refuse(
            lambda: (_ for _ in ()).throw(RuntimeError("inner")),
            enabled=broker_compute_enabled,
            broker_only=broker_compute_only,
            msg="env refuse",
        )

    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    assert (
        try_or_refuse(
            lambda: (_ for _ in ()).throw(RuntimeError("inner")),
            enabled=broker_compute_enabled,
            broker_only=broker_compute_only,
            msg="env refuse",
        )
        is None
    )
