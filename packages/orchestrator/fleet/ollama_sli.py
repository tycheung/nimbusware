from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from env.env_flags import env_str
from env.settings_resolve import resolve_int, resolve_raw
from orchestrator.preflight_histogram import build_histogram, nearest_rank_p95

SCHEMA_VERSION = 1
DEFAULT_EXPORT_PATH = Path(".cache/fleet_ollama_sli.json")


def fleet_ollama_sli_enabled() -> bool:
    try:
        from env.edition import enterprise_feature_enabled

        return enterprise_feature_enabled("fleet_ollama_sli")
    except ImportError:
        return False


def _bounded_int(key: str, default: int, *, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, resolve_int(key, default=default)))


def _bounded_float(key: str, default: float, *, minimum: float) -> float:
    raw = resolve_raw(key)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(minimum, float(str(raw).strip()))
    except ValueError:
        return default


def sustained_probe_config() -> dict[str, Any]:
    return {
        "samples": _bounded_int(
            "NIMBUSWARE_FLEET_OLLAMA_SLI_SAMPLES",
            60,
            minimum=1,
            maximum=500,
        ),
        "interval_seconds": _bounded_float(
            "NIMBUSWARE_FLEET_OLLAMA_SLI_INTERVAL_SEC",
            5.0,
            minimum=0.0,
        ),
        "timeout_seconds": _bounded_float(
            "NIMBUSWARE_FLEET_OLLAMA_SLI_TIMEOUT_SEC",
            30.0,
            minimum=1.0,
        ),
    }


def export_path() -> Path:
    raw = env_str("NIMBUSWARE_FLEET_OLLAMA_SLI_EXPORT_PATH")
    return Path(raw) if raw else DEFAULT_EXPORT_PATH


def resolve_runtime_url(*, base_url: str | None = None) -> str:
    if base_url and base_url.strip():
        return base_url.strip().rstrip("/")
    env_url = env_str("NIMBUSWARE_FLEET_OLLAMA_SLI_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    return "http://localhost:11434"


def resolve_health_path() -> str:
    raw = env_str("NIMBUSWARE_FLEET_OLLAMA_SLI_HEALTH_PATH")
    return raw or "/api/tags"


def probe_health_latency_ms(
    *,
    base_url: str,
    health_path: str,
    timeout_seconds: float,
) -> tuple[bool, int, str | None]:
    url = urljoin(base_url.rstrip("/") + "/", health_path.lstrip("/"))
    t0 = time.monotonic()
    try:
        r = httpx.get(url, timeout=timeout_seconds)
        r.raise_for_status()
        return True, int((time.monotonic() - t0) * 1000), None
    except (httpx.HTTPError, ValueError) as exc:
        return False, int((time.monotonic() - t0) * 1000), str(exc)[:200]


def run_sustained_health_probe(
    *,
    base_url: str | None = None,
    health_path: str | None = None,
    samples: int | None = None,
    interval_seconds: float | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Sequential health GET probes for fleet-wide sustained p95 SLI."""
    cfg = sustained_probe_config()
    n = samples if samples is not None else int(cfg["samples"])
    interval = interval_seconds if interval_seconds is not None else float(cfg["interval_seconds"])
    timeout = timeout_seconds if timeout_seconds is not None else float(cfg["timeout_seconds"])
    url = resolve_runtime_url(base_url=base_url)
    path = health_path or resolve_health_path()
    started = datetime.now(timezone.utc)
    latencies: list[int] = []
    errors: list[str] = []
    for i in range(n):
        ok, ms, err = probe_health_latency_ms(
            base_url=url,
            health_path=path,
            timeout_seconds=timeout,
        )
        latencies.append(ms)
        if not ok and err:
            errors.append(err)
        if i + 1 < n and interval > 0:
            time.sleep(interval)
    finished = datetime.now(timezone.utc)
    histogram = build_histogram(latencies)
    p95 = nearest_rank_p95(latencies)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "fleet_ollama_sustained_sli",
        "generated_at": finished.isoformat(),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "base_url": url,
        "health_path": path,
        "samples_requested": n,
        "samples_used": len(latencies),
        "probe_errors": errors[:20],
        "success_ratio": (n - len(errors)) / n if n else 0.0,
        "p95_latency_ms": p95,
        "histogram": histogram,
    }


def write_sli_export(record: dict[str, Any], path: Path | str | None = None) -> Path:
    target = Path(path) if path is not None else export_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, separators=(",", ":")) + "\n", encoding="utf-8")
    return target


def read_sli_export(path: Path | str | None = None) -> dict[str, Any] | None:
    target = Path(path) if path is not None else export_path()
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def merge_preflight_history_aggregate(
    preflight_history: dict[str, Any],
    *,
    sustained: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach sustained SLI export to ``GET /v1/preflight-history`` aggregates."""
    sustained = sustained if sustained is not None else read_sli_export()
    hist_max = preflight_history.get("max_p95_latency_ms")
    sustained_p95 = None
    if isinstance(sustained, dict):
        raw = sustained.get("p95_latency_ms")
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            sustained_p95 = raw
    combined_max: int | None = None
    for candidate in (hist_max, sustained_p95):
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            if combined_max is None or candidate > combined_max:
                combined_max = candidate
    metrics_export = preflight_history.get("metrics_export")
    fleet_sli: dict[str, Any] = {
        "feature": "fleet_ollama_sli",
        "sustained_export_present": sustained is not None,
        "sustained_p95_latency_ms": sustained_p95,
        "history_max_p95_latency_ms": hist_max,
        "combined_max_p95_latency_ms": combined_max,
    }
    if isinstance(metrics_export, dict):
        fleet_sli["history_metrics_export"] = {
            "export_schema_version": metrics_export.get("export_schema_version"),
            "runs_scanned": metrics_export.get("runs_scanned"),
            "avg_p95_latency_ms": metrics_export.get("avg_p95_latency_ms"),
            "p95_latency_coverage_ratio": metrics_export.get("p95_latency_coverage_ratio"),
        }
    return {
        "preflight_history": preflight_history,
        "sustained_sli": sustained,
        "fleet_sli": fleet_sli,
    }


def fleet_ollama_sli_status_snapshot() -> dict[str, Any]:
    sustained = read_sli_export()
    cfg = sustained_probe_config()
    return {
        "feature": "fleet_ollama_sli",
        "fleet_profile_enabled": fleet_ollama_sli_enabled(),
        "export_path": str(export_path()),
        "sustained_export_present": sustained is not None,
        "sustained_p95_latency_ms": (
            sustained.get("p95_latency_ms") if isinstance(sustained, dict) else None
        ),
        "probe_config": cfg,
        "sustained": sustained,
    }
