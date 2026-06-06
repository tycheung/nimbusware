"""Utility helpers for token budget golden fixtures."""

CACHE = {f"k{i}": "v" * 40 for i in range(80)}


def helper() -> str:
    return "util"
