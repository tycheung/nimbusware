from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException

from api.routes.enterprise import research_ops as ro
from executor.broker_route import map_broker_egress_http_miss
from executor.fetch import egress_checked_httpx_get


def test_map_egress_miss_under_egress_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: map_broker_egress_http_miss returns broker_miss under EGRESS=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    out = map_broker_egress_http_miss(
        RuntimeError("broker_miss: egress: down"),
        feature="egress",
    )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "egress"
    assert out.get("status") == "degraded"


def test_map_egress_miss_under_egress_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: map_broker_egress_http_miss maps to 503 under EGRESS=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "2")
    with pytest.raises(HTTPException) as ei:
        map_broker_egress_http_miss(
            RuntimeError("broker_miss: egress: down"),
            feature="egress",
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_egress_only"


def test_egress_checked_under_egress_1_broker_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: egress_checked_httpx_get raises broker_miss under EGRESS=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    role = UUID("11111111-1111-4111-8111-111111111101")
    client = MagicMock(spec=httpx.Client)
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: egress"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )
    client.get.assert_not_called()


def test_egress_audit_under_egress_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: enterprise egress-audit JSON returns broker_miss under EGRESS=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    resp = ro.enterprise_egress_audit(_gate=object(), format="json")  # type: ignore[arg-type]
    body = json.loads(resp.body.decode("utf-8"))
    assert body.get("via") == "broker_miss"
    assert body.get("feature") == "egress_audit"
    assert body.get("status") == "degraded"


def test_egress_audit_under_egress_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: enterprise egress-audit JSON maps to 503 under EGRESS=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "2")
    with pytest.raises(HTTPException) as ei:
        ro.enterprise_egress_audit(_gate=object(), format="json")  # type: ignore[arg-type]
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_egress_only"
