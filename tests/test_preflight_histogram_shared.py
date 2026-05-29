"""Tests for the shared `hermes_orchestrator.preflight_histogram` module.

The histogram helpers were lifted out of ``preflight_cli.py`` in fo124 so two
callers (CLI + Streamlit console) share the same bucket edges and stat math.
This file asserts the public surface (``BUCKET_EDGES_MS``, ``build_histogram``,
``empty_histogram``, ``nearest_rank_p95``) and confirms that the fo123 CLI
aliases (``preflight_cli._BUCKET_EDGES_MS`` etc.) still point at the shared
implementation for backward compatibility.
"""

from __future__ import annotations

from hermes_orchestrator import preflight_cli, preflight_histogram


def test_bucket_edges_ms_is_fixed_tuple() -> None:
    assert isinstance(preflight_histogram.BUCKET_EDGES_MS, tuple)
    assert preflight_histogram.BUCKET_EDGES_MS == (
        50,
        100,
        250,
        500,
        1000,
        2500,
        5000,
        10000,
    )


def test_cli_aliases_point_at_shared_implementation() -> None:
    """fo123 internal names still resolve to the lifted helpers (no caller breakage)."""
    assert preflight_cli._BUCKET_EDGES_MS is preflight_histogram.BUCKET_EDGES_MS
    assert preflight_cli._build_histogram is preflight_histogram.build_histogram
    assert preflight_cli._empty_histogram is preflight_histogram.empty_histogram


def test_empty_histogram_zeroed_with_expected_keys() -> None:
    h = preflight_histogram.empty_histogram()
    assert h["count"] == 0
    assert h["samples_ms"] == []
    assert h["min_ms"] is None
    assert h["max_ms"] is None
    assert h["mean_ms"] is None
    assert h["median_ms"] is None
    assert h["p95_ms"] is None
    # 8 named buckets + 1 overflow ⇒ 9 entries with le_ms=None last
    assert len(h["buckets"]) == 9
    assert h["buckets"][-1]["le_ms"] is None
    assert all(b["count"] == 0 for b in h["buckets"])


def test_nearest_rank_p95_matches_orchestrator_parity() -> None:
    # Round-trip a known sequence through both shared p95 and the orchestrator's
    # private one to confirm algorithm parity. The shared version is the only
    # one called by the CLI / console, but parity is important for downstream
    # operators correlating CLI output with orchestrator-side evidence.
    from hermes_orchestrator import preflight as _orch_preflight

    seq = [10, 50, 200, 1500, 9000]
    assert preflight_histogram.nearest_rank_p95(seq) == _orch_preflight._nearest_rank_p95(seq)


def test_build_histogram_partition_sum_invariant() -> None:
    """The fundamental contract: bucket counts sum to total count."""
    samples = [0, 1, 49, 50, 51, 100, 250, 251, 9999, 10_000, 10_001, 25_000]
    h = preflight_histogram.build_histogram(samples)
    assert h["count"] == len(samples)
    assert sum(b["count"] for b in h["buckets"]) == len(samples)
    # 0 sample lands in (-1, 50] (sentinel makes degenerate skip-preflight
    # 0ms evidence countable rather than dropped) — fo124 lift preserved this.
    by_edge = {b["le_ms"]: b["count"] for b in h["buckets"]}
    assert by_edge[50] >= 4  # 0, 1, 49, 50
    assert by_edge[None] == 2  # 10_001, 25_000 overflow


def test_build_histogram_preserves_chronological_order_in_samples_ms() -> None:
    samples = [500, 100, 9000, 50]
    h = preflight_histogram.build_histogram(samples)
    # samples_ms must NOT be sorted (operators need the time-series ordering)
    assert h["samples_ms"] == [500, 100, 9000, 50]
    # but min/max/mean/median/p95 are calculated on sorted data
    assert h["min_ms"] == 50
    assert h["max_ms"] == 9000
