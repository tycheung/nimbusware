"""Preflight latency statistics helpers."""

from __future__ import annotations

import importlib


def test_nearest_rank_p95() -> None:
    preflight = importlib.import_module("hermes_orchestrator.preflight")
    p95 = preflight._nearest_rank_p95([10, 50, 50, 50, 100])
    assert p95 == 100
