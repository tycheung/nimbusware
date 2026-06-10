from __future__ import annotations

from nimbusware_orchestrator.interaction_surface_map import exploratory_crawl_limits


def test_exploratory_crawl_limits_defaults(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_CLICKS", raising=False)
    monkeypatch.delenv("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_DEPTH", raising=False)
    clicks, depth = exploratory_crawl_limits()
    assert clicks == 12
    assert depth == 3


def test_exploratory_crawl_limits_env_override(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_CLICKS", "20")
    monkeypatch.setenv("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_DEPTH", "4")
    clicks, depth = exploratory_crawl_limits()
    assert clicks == 20
    assert depth == 4
