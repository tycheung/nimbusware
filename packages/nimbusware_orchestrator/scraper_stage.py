from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class ScraperFetchConfig:
    """Workflow ``scraper_fetch`` block (``configs/workflows/*.yaml``)."""

    enabled: bool
    fetch_urls: tuple[str, ...]
    actor_role_key: str
    max_attempts: int
    backoff_seconds: float
    max_bytes: int | None
    body_snippet_max_bytes: int
    # When set (positive), persist up to this many bytes per response under artifact base dir.
    # ``None`` / omitted YAML: no on-disk response bodies (snippets/digests still in events).
    persist_artifacts_max_bytes_per_url: int | None


def load_scraper_fetch_config(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> ScraperFetchConfig:
    raw = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    block = raw.get("scraper_fetch")
    if not isinstance(block, dict):
        return ScraperFetchConfig(
            enabled=False,
            fetch_urls=tuple(),
            actor_role_key="backend_writer",
            max_attempts=1,
            backoff_seconds=0.0,
            max_bytes=None,
            body_snippet_max_bytes=256,
            persist_artifacts_max_bytes_per_url=None,
        )
    enabled = bool(block.get("enabled", False))
    url_raw = block.get("url")
    single = str(url_raw).strip() if url_raw is not None else ""
    fetch_urls: list[str] = []
    urls_raw = block.get("urls")
    if isinstance(urls_raw, list):
        for x in urls_raw:
            if x is None:
                continue
            u = str(x).strip()
            if u:
                fetch_urls.append(u)
    if not fetch_urls and single:
        fetch_urls = [single]
    key = str(block.get("actor_role_key", "backend_writer")).strip() or "backend_writer"
    try:
        ma = int(block.get("max_attempts", 1))
    except (TypeError, ValueError):
        ma = 1
    ma = min(max(ma, 1), 10)
    try:
        bo = float(block.get("backoff_seconds", 0) or 0)
    except (TypeError, ValueError):
        bo = 0.0
    bo = min(max(bo, 0.0), 60.0)
    mb_raw = block.get("max_bytes")
    max_bytes: int | None = None
    if isinstance(mb_raw, int) and mb_raw >= 0:
        max_bytes = mb_raw
    try:
        sn = int(block.get("body_snippet_max_bytes", 256))
    except (TypeError, ValueError):
        sn = 256
    sn = min(max(sn, 0), 4096)
    pa_raw = block.get("persist_artifacts_max_bytes_per_url")
    persist_art: int | None = None
    if isinstance(pa_raw, int) and pa_raw > 0:
        persist_art = min(pa_raw, 2_097_152)  # cap at 2 MiB per URL
    return ScraperFetchConfig(
        enabled=enabled,
        fetch_urls=tuple(fetch_urls),
        actor_role_key=key,
        max_attempts=ma,
        backoff_seconds=bo,
        max_bytes=max_bytes,
        body_snippet_max_bytes=sn,
        persist_artifacts_max_bytes_per_url=persist_art,
    )
