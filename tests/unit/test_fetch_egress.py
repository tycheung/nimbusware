"""egress_checked_httpx_get with mocked HTTP client."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import httpx

from nimbusware_executor.fetch import egress_checked_httpx_get


def test_egress_checked_get_invokes_httpx_after_policy() -> None:
    role = UUID("11111111-1111-4111-8111-111111111101")
    allow = [role]
    domains = ["example.com"]
    mock_resp = MagicMock(spec=httpx.Response)
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp
    resp = egress_checked_httpx_get(
        "https://example.com/path",
        actor_role_id=role,
        scraper_role_allowlist=allow,
        domain_allowlist=domains,
        client=client,
    )
    assert resp is mock_resp
    client.get.assert_called_once()
