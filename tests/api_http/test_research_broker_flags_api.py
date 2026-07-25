from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from research.broker_route import map_broker_research_http_miss
from research.fetch import fetch_url


def test_map_research_miss_under_research_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: map_broker_research_http_miss returns broker_miss under RESEARCH=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    out = map_broker_research_http_miss(
        RuntimeError("broker_miss: research_fetch: down"),
        feature="research_fetch",
    )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "research_fetch"
    assert out.get("status") == "degraded"


def test_map_research_miss_under_research_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: map_broker_research_http_miss maps to 503 under RESEARCH=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "2")
    with pytest.raises(HTTPException) as ei:
        map_broker_research_http_miss(
            RuntimeError("broker_miss: research_fetch: down"),
            feature="research_fetch",
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_research_only"


def test_fetch_url_under_research_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: fetch_url raises broker_miss under RESEARCH=1 when broker returns None."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: research_fetch"):
        fetch_url("https://example.com/page")


def test_fetch_url_under_research_1_broker_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: fetch_url returns broker payload under RESEARCH=1 on hit."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: {"body": "page text"},
    )
    out = fetch_url("https://example.com/page")
    assert out.get("backend") == "broker"
    assert out.get("body") == "page text"
