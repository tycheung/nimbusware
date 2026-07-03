from __future__ import annotations

import math
from typing import Any

BUCKET_EDGES_MS: tuple[int, ...] = (50, 100, 250, 500, 1000, 2500, 5000, 10000)


def nearest_rank_p95(samples_ms: list[int]) -> int:
    """Parity with :func:`orchestrator.preflight._nearest_rank_p95`.

    Kept here so the CLI / console don't have to import the orchestrator's
    leading-underscore private name; algorithm is intentionally identical so
    derived percentiles match orchestrator-side evidence.
    """
    if not samples_ms:
        return 0
    s = sorted(samples_ms)
    n = len(s)
    k = max(1, math.ceil(0.95 * n))
    return s[k - 1]


def empty_histogram() -> dict[str, Any]:
    return {
        "samples_ms": [],
        "count": 0,
        "min_ms": None,
        "max_ms": None,
        "mean_ms": None,
        "median_ms": None,
        "p95_ms": None,
        "buckets": [
            *({"le_ms": e, "count": 0} for e in BUCKET_EDGES_MS),
            {"le_ms": None, "count": 0},
        ],
        "bucket_edges_ms": list(BUCKET_EDGES_MS),
    }


def build_histogram(samples_ms: list[int]) -> dict[str, Any]:
    """Summarise integer-millisecond latency samples into a JSON histogram.

    ``samples_ms`` is preserved in CHRONOLOGICAL order (it is a time series of
    sequential probes). Stats are derived from a defensively sorted copy.
    Buckets are non-cumulative and partition ``(prev_edge, le_ms]``; the
    trailing ``{le_ms: None}`` entry collects everything above the last edge.
    The sentinel ``prev_edge = -1`` in the first iteration ensures a 0ms
    sample (only emitted on ``NIMBUSWARE_SKIP_PREFLIGHT``'s synthetic evidence)
    still lands in the first bucket — real probe latencies are always >= 1ms
    so this only adjusts a degenerate edge case.
    """
    if not samples_ms:
        return empty_histogram()
    sorted_samples = sorted(samples_ms)
    n = len(samples_ms)
    mean_ms = sum(samples_ms) // n
    if n % 2 == 1:
        median_ms = sorted_samples[n // 2]
    else:
        median_ms = (sorted_samples[n // 2 - 1] + sorted_samples[n // 2]) // 2
    buckets: list[dict[str, Any]] = []
    prev_edge = -1
    for edge in BUCKET_EDGES_MS:
        bucket_count = sum(1 for s in samples_ms if prev_edge < s <= edge)
        buckets.append({"le_ms": edge, "count": bucket_count})
        prev_edge = edge
    overflow = sum(1 for s in samples_ms if s > BUCKET_EDGES_MS[-1])
    buckets.append({"le_ms": None, "count": overflow})
    return {
        "samples_ms": list(samples_ms),
        "count": n,
        "min_ms": min(samples_ms),
        "max_ms": max(samples_ms),
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "p95_ms": nearest_rank_p95(samples_ms),
        "buckets": buckets,
        "bucket_edges_ms": list(BUCKET_EDGES_MS),
    }
