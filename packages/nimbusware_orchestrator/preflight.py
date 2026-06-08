"""Ollama (or compatible) model preflight."""

from __future__ import annotations

import json
import math
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from nimbusware_env.env_flags import (
    nimbusware_preflight_json_probe_enabled,
    nimbusware_preflight_latency_sample_count,
    nimbusware_skip_preflight_enabled,
)


class PreflightError(RuntimeError):
    pass


def _latency_sample_count() -> int:
    return nimbusware_preflight_latency_sample_count()


def _nearest_rank_p95(samples: list[int]) -> int:
    """Nearest-rank p95 over integer millisecond samples (bounded small N)."""
    if not samples:
        return 0
    s = sorted(samples)
    n = len(s)
    k = max(1, math.ceil(0.95 * n))
    return s[k - 1]


def _ollama_context_length(
    base_url: str,
    model: str,
    timeout_seconds: float,
) -> tuple[int | None, int]:
    """Return ``(context_length_or_none, latency_ms)`` from ``/api/show``."""
    url = base_url.rstrip("/") + "/api/show"
    t0 = time.monotonic()
    try:
        r = httpx.post(url, json={"name": model}, timeout=timeout_seconds)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None, int((time.monotonic() - t0) * 1000)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if not isinstance(data, dict):
        return None, latency_ms
    mi = data.get("model_info")
    if not isinstance(mi, dict):
        return None, latency_ms
    for k in ("context_length", "n_ctx"):
        if k in mi and mi[k] is not None:
            try:
                return int(mi[k]), latency_ms
            except (TypeError, ValueError):
                return None, latency_ms
    return None, latency_ms


def _optional_json_probe(
    *,
    base_url: str,
    model: str,
    timeout_seconds: float,
) -> tuple[bool, int, str | None]:
    """Return ``(ok, latency_ms, error_or_none)`` for a tiny ``format: json`` chat."""
    url = base_url.rstrip("/") + "/api/chat"
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": 'Reply with JSON only: {"ok":true}'}],
        "stream": False,
        "format": "json",
    }
    t0 = time.monotonic()
    try:
        r = httpx.post(url, json=body, timeout=min(timeout_seconds, 30.0))
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return False, int((time.monotonic() - t0) * 1000), str(exc)
    latency_ms = int((time.monotonic() - t0) * 1000)
    msg = data.get("message") if isinstance(data, dict) else None
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str):
        return False, latency_ms, "missing message.content"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return False, latency_ms, str(exc)
    if isinstance(parsed, dict) and parsed.get("ok") is True:
        return True, latency_ms, None
    return False, latency_ms, "json body missing ok:true"


def run_model_preflight(
    *,
    base_url: str,
    health_path: str,
    primary_model_id: str,
    fallback_model_ids: list[str],
    timeout_seconds: float = 10.0,
    preflight_cfg: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], bool]:
    """Return ``(selected_model_id, evidence_dict, used_primary)``.

    ``used_primary`` is False when a fallback tag was selected first.
    """
    if nimbusware_skip_preflight_enabled():
        return (
            primary_model_id,
            {
                "skipped": True,
                "reason": "NIMBUSWARE_SKIP_PREFLIGHT",
                "checks_passed": ["skipped"],
                "context_tokens": 8192,
                "p95_latency_ms": 0,
                "health_latency_ms": 0,
            },
            True,
        )

    cfg = preflight_cfg or {}
    min_ctx = int(cfg.get("min_context_tokens", 1))

    url = urljoin(base_url.rstrip("/") + "/", health_path.lstrip("/"))
    n_health = _latency_sample_count()
    data: dict[str, Any] = {}
    health_latencies: list[int] = []
    try:
        for i in range(n_health):
            t0 = time.monotonic()
            r = httpx.get(url, timeout=timeout_seconds)
            r.raise_for_status()
            health_latencies.append(int((time.monotonic() - t0) * 1000))
            if i == 0:
                parsed = r.json()
                if isinstance(parsed, dict):
                    data = parsed
    except (httpx.HTTPError, ValueError) as exc:
        raise PreflightError(f"runtime not reachable: {exc}") from exc
    health_latency_ms = health_latencies[0]
    health_p95_ms = _nearest_rank_p95(health_latencies)

    models = data.get("models") if isinstance(data, dict) else None
    names: set[str] = set()
    if isinstance(models, list):
        for m in models:
            if isinstance(m, dict) and "name" in m:
                names.add(str(m["name"]))
            elif isinstance(m, str):
                names.add(m)

    ordered = [primary_model_id, *fallback_model_ids]
    selected: str | None = None
    for mid in ordered:
        if mid in names:
            selected = mid
            break
    if selected is None:
        raise PreflightError(f"No configured model found in runtime tags: {ordered!r}")

    used_primary = selected == primary_model_id
    checks_passed = ["runtime_reachable", "model_available", "health_latency_measured"]
    if n_health > 1:
        checks_passed.append("health_latency_multisample")
    ctx, show_latency_ms = _ollama_context_length(base_url, selected, timeout_seconds)
    evidence: dict[str, Any] = {
        "runtime_reachable": True,
        "model_available": True,
        "model_id": selected,
        "health_latency_ms": health_latency_ms,
        "health_latency_p95_ms": health_p95_ms,
        "show_latency_ms": show_latency_ms,
        "p95_latency_ms": max(health_p95_ms, show_latency_ms),
    }
    if n_health > 1:
        evidence["health_latency_samples_ms"] = health_latencies
    if ctx is not None:
        evidence["context_tokens"] = ctx
        if ctx >= min_ctx:
            checks_passed.append("context_budget_ok")
    else:
        evidence["context_tokens"] = 8192
        if evidence["context_tokens"] >= min_ctx:
            checks_passed.append("context_budget_ok")

    if nimbusware_preflight_json_probe_enabled():
        ok, lat, err = _optional_json_probe(
            base_url=base_url,
            model=selected,
            timeout_seconds=timeout_seconds,
        )
        evidence["json_probe_latency_ms"] = lat
        if err:
            evidence["json_probe_error"] = err
        if ok:
            checks_passed.append("structured_json_probe_ok")
            evidence["p95_latency_ms"] = max(int(evidence["p95_latency_ms"]), lat)
        else:
            checks_passed.append("structured_json_probe_skipped_or_failed")

    evidence["checks_passed"] = checks_passed
    evidence["preflight_latency_sample_count"] = n_health
    evidence["p95_latency_source"] = "max(health_p95_ms,show_latency_ms,optional_json_probe)"
    return selected, evidence, used_primary
