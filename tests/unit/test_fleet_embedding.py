from __future__ import annotations

import pytest

from memory.index.embeddings import resolve_fleet_embedding_mode


def test_resolve_fleet_embedding_mode_explicit() -> None:
    assert resolve_fleet_embedding_mode("deterministic") == "deterministic"
    assert resolve_fleet_embedding_mode("ollama") == "ollama"


def test_resolve_fleet_embedding_mode_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "0")
    assert resolve_fleet_embedding_mode(None) == "deterministic"
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    assert resolve_fleet_embedding_mode(None) == "ollama"
