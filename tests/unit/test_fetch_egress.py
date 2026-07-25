from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest

from executor.fetch import egress_checked_httpx_get


def test_egress_checked_get_invokes_httpx_after_broker_allow(
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
        "https://example.com/path",
        actor_role_id=role,
        scraper_role_allowlist=[role],
        domain_allowlist=["example.com"],
        client=client,
    )
    assert resp is mock_resp
    client.get.assert_called_once()


def test_egress_checked_get_raises_when_broker_none(
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
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )
    client.get.assert_not_called()
