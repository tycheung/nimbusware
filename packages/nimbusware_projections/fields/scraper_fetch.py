"""Scraper fetch projection field metadata."""

from __future__ import annotations

SCRAPER_FETCH_ROW_KEYS: tuple[str, ...] = (
    "url_host",
    "http_status",
    "bytes",
    "attempts",
    "content_length",
    "artifact_relpath",
)

__all__ = ["SCRAPER_FETCH_ROW_KEYS"]
