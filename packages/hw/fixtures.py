from __future__ import annotations

from typing import Any

FIXTURE_NAMES = frozenset({"weak", "medium", "strong"})


def fixture_probe(name: str) -> dict[str, Any]:
    key = name.strip().lower()
    if key not in FIXTURE_NAMES:
        msg = f"unknown hardware fixture: {name!r}"
        raise ValueError(msg)
    if key == "weak":
        return {
            "tier": "weak",
            "ram_total_gb": 8.0,
            "ram_available_gb": 3.5,
            "cpu_count": 2,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "fixture",
            "fixture": key,
        }
    if key == "medium":
        return {
            "tier": "medium",
            "ram_total_gb": 16.0,
            "ram_available_gb": 10.0,
            "cpu_count": 6,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "fixture",
            "fixture": key,
        }
    return {
        "tier": "strong",
        "ram_total_gb": 64.0,
        "ram_available_gb": 48.0,
        "cpu_count": 16,
        "gpus": [{"name": "fixture-gpu", "vram_gb": 24.0, "backend": "cuda"}],
        "gpu_groups": [["fixture-gpu"]],
        "unified_memory": False,
        "errors": [],
        "platform": "fixture",
        "fixture": key,
    }
