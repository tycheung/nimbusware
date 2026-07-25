from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest

from executor.egress_bridge import try_broker_egress_check
from executor.fetch import egress_checked_httpx_get


def test_try_broker_egress_check_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_EGRESS", raising=False)
    assert try_broker_egress_check("https://example.com") is None


def test_try_broker_egress_check_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    monkeypatch.setattr(
        "executor.egress_bridge.egress_check_via_broker",
        lambda url: {"allowed": True, "url": url},
    )

    out = try_broker_egress_check("https://example.com")

    assert out == {"allowed": True, "url": "https://example.com"}


def test_try_broker_egress_check_exception_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    monkeypatch.setattr(
        "executor.egress_bridge.egress_check_via_broker",
        lambda _url: (_ for _ in ()).throw(RuntimeError("broker down")),
    )
    assert try_broker_egress_check("https://example.com") is None


def test_try_broker_egress_check_broker_only_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "2")
    monkeypatch.setattr(
        "executor.egress_bridge.egress_check_via_broker",
        lambda _url: (_ for _ in ()).throw(RuntimeError("broker down")),
    )
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_egress_check("https://example.com")


def test_egress_checked_httpx_get_broker_allowed_skips_local_assert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role = UUID("11111111-1111-4111-8111-111111111101")
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: {"allowed": True},
    )
    mock_resp = MagicMock(spec=httpx.Response)
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp

    resp = egress_checked_httpx_get(
        "https://blocked.example/path",
        actor_role_id=role,
        scraper_role_allowlist=[],
        domain_allowlist=["example.com"],
        client=client,
    )

    assert resp is mock_resp
    client.get.assert_called_once()


def test_egress_checked_httpx_get_broker_denied_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role = UUID("11111111-1111-4111-8111-111111111101")
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: {"allowed": False, "reason": "policy.denied"},
    )
    client = MagicMock(spec=httpx.Client)

    with pytest.raises(PermissionError, match="policy.denied"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )

    client.get.assert_not_called()


def test_egress_checked_httpx_get_broker_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role = UUID("11111111-1111-4111-8111-111111111101")
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: None,
    )
    client = MagicMock(spec=httpx.Client)

    with pytest.raises(RuntimeError, match="local egress removed"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[],
            domain_allowlist=["example.com"],
            client=client,
        )

    client.get.assert_not_called()
