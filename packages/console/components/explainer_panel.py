from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal


def explainer_utc_timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def nimbusware_download_filename(
    slug: str,
    ts: str,
    *,
    kind: Literal["metrics", "explainer"],
    ext: str,
) -> str:
    if kind == "explainer":
        return f"nimbusware_{slug}_explainer_{ts}.{ext}"
    return f"nimbusware_{slug}_{ts}.{ext}"
