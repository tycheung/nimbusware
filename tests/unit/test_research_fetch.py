from __future__ import annotations

import pytest

from research.fetch import fetch_url


def test_fetch_url_broker_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda url: {"body": "html", "url": url},
    )

    out = fetch_url("https://example.com")
    assert out == {
        "backend": "broker",
        "body": "html",
        "url": "https://example.com",
    }


def test_fetch_url_broker_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: None,
    )

    with pytest.raises(RuntimeError, match="research local fetch removed"):
        fetch_url("https://example.com/page")
