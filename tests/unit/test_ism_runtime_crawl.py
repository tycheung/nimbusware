from __future__ import annotations

from orchestrator.interaction_surface_map import (
    InteractionSurfaceMap,
    discover_surfaces_runtime,
)


def test_discover_surfaces_runtime_empty_on_bad_url() -> None:
    ism = discover_surfaces_runtime("http://127.0.0.1:1", max_links=5)
    assert isinstance(ism, InteractionSurfaceMap)
    assert ism.source == "runtime_crawl"
