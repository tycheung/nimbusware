"""Aggregate token/latency hints from event metadata per role."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from agent_core.models import EventType
from nimbusware_orchestrator.registry import RoleRegistry

ROLE_TELEMETRY_METADATA_KEY = "role_telemetry"

_STAGE_TO_ROLE_KEY: dict[str, str] = {
    "plan": "planner",
    "implementation": "backend_writer",
    "test_writer": "test_writer",
    "frontend_writer": "frontend_writer",
    "slice.implement": "backend_writer",
    "slice.verify": "backend_writer",
    "slice.test": "test_writer",
    "slice.gate": "planner",
}


def merge_role_telemetry_metadata(
    metadata: dict[str, Any] | None,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Merge conventional ``metadata.role_telemetry`` hints (for LLM call sites)."""
    base: dict[str, Any] = dict(metadata or {})
    existing = base.get(ROLE_TELEMETRY_METADATA_KEY)
    hint: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    if prompt_tokens is not None:
        hint["prompt_tokens"] = int(prompt_tokens)
    if completion_tokens is not None:
        hint["completion_tokens"] = int(completion_tokens)
    if latency_ms is not None:
        hint["latency_ms"] = int(latency_ms)
    if model_id is not None and str(model_id).strip():
        hint["model_id"] = str(model_id).strip()
    if hint:
        base[ROLE_TELEMETRY_METADATA_KEY] = hint
    return base


def extract_role_telemetry_hint(row: dict[str, Any]) -> dict[str, Any] | None:
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        return None
    hint = meta.get(ROLE_TELEMETRY_METADATA_KEY)
    return dict(hint) if isinstance(hint, dict) else None


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return ordered[idx]


def _role_key_from_stage(stage_name: str | None) -> str | None:
    if not isinstance(stage_name, str) or not stage_name.strip():
        return None
    sn = stage_name.strip()
    if sn in _STAGE_TO_ROLE_KEY:
        return _STAGE_TO_ROLE_KEY[sn]
    if sn.endswith(".critique"):
        return sn.split(".", 1)[0]
    return sn


def _resolve_role_key(
    role_id: UUID | str | None,
    *,
    registry: RoleRegistry | None,
    fallback: str | None = None,
) -> str:
    if registry is not None and role_id is not None:
        try:
            rid = role_id if isinstance(role_id, UUID) else UUID(str(role_id))
        except ValueError:
            rid = None
        if rid is not None:
            key = registry.taxonomy_key_for(rid)
            if key:
                return key
    if fallback:
        return fallback
    if role_id is not None:
        return str(role_id)
    return "unknown"


@dataclass
class _RoleBucket:
    role_key: str
    role_id: str | None = None
    event_count: int = 0
    model_counts: dict[str, int] = field(default_factory=dict)
    duration_ms_total: int = 0
    duration_ms_samples: list[int] = field(default_factory=list)
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    latency_ms_samples: list[int] = field(default_factory=list)


@dataclass
class _PreflightAccumulator:
    samples: list[dict[str, Any]] = field(default_factory=list)

    def add(self, payload: dict[str, Any]) -> None:
        self.samples.append(
            {
                "validated_model_id": payload.get("validated_model_id"),
                "context_tokens": payload.get("context_tokens"),
                "p95_latency_ms": payload.get("p95_latency_ms"),
            },
        )


def _bucket_for(
    buckets: dict[str, _RoleBucket],
    role_key: str,
    *,
    role_id: str | None = None,
) -> _RoleBucket:
    if role_key not in buckets:
        buckets[role_key] = _RoleBucket(role_key=role_key, role_id=role_id)
    bucket = buckets[role_key]
    if role_id and not bucket.role_id:
        bucket.role_id = role_id
    return bucket


def accumulate_event_row(
    buckets: dict[str, _RoleBucket],
    preflight: _PreflightAccumulator,
    row: dict[str, Any],
    *,
    registry: RoleRegistry | None = None,
) -> None:
    et = str(row.get("event_type", ""))
    pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    model_id = row.get("model_id")
    model_s = str(model_id).strip() if model_id else None

    hint = extract_role_telemetry_hint(row)
    if hint:
        role_key = _resolve_role_key(row.get("actor_role"), registry=registry, fallback="unknown")
        bucket = _bucket_for(buckets, role_key)
        bucket.event_count += 1
        if model_s:
            bucket.model_counts[model_s] = bucket.model_counts.get(model_s, 0) + 1
        pt = hint.get("prompt_tokens")
        ct = hint.get("completion_tokens")
        lat = hint.get("latency_ms")
        if isinstance(pt, int):
            bucket.prompt_tokens_total += pt
        elif isinstance(pt, str) and pt.isdigit():
            bucket.prompt_tokens_total += int(pt)
        if isinstance(ct, int):
            bucket.completion_tokens_total += ct
        elif isinstance(ct, str) and ct.isdigit():
            bucket.completion_tokens_total += int(ct)
        if isinstance(lat, int):
            bucket.latency_ms_samples.append(lat)
        elif isinstance(lat, str) and lat.isdigit():
            bucket.latency_ms_samples.append(int(lat))
        hint_model = hint.get("model_id")
        if isinstance(hint_model, str) and hint_model.strip():
            bucket.model_counts[hint_model.strip()] = (
                bucket.model_counts.get(hint_model.strip(), 0) + 1
            )

    if et == EventType.MODEL_PREFLIGHT_PASSED.value and isinstance(pl, dict):
        preflight.add(pl)
        return

    if et in (EventType.STAGE_PASSED.value, EventType.STAGE_FAILED.value) and isinstance(pl, dict):
        stage_name = pl.get("stage_name")
        role_key = (
            _role_key_from_stage(
                str(stage_name) if stage_name is not None else None,
            )
            or "stage"
        )
        bucket = _bucket_for(buckets, role_key)
        bucket.event_count += 1
        if model_s:
            bucket.model_counts[model_s] = bucket.model_counts.get(model_s, 0) + 1
        dur = pl.get("duration_ms")
        if isinstance(dur, int):
            bucket.duration_ms_total += dur
            bucket.duration_ms_samples.append(dur)
        return

    if et == EventType.CRITIC_VERDICT_EMITTED.value and isinstance(pl, dict):
        critic = pl.get("critic_role")
        role_key = _resolve_role_key(critic, registry=registry, fallback="critic")
        bucket = _bucket_for(
            buckets,
            role_key,
            role_id=str(critic) if critic is not None else None,
        )
        bucket.event_count += 1
        if model_s:
            bucket.model_counts[model_s] = bucket.model_counts.get(model_s, 0) + 1
        return

    actor = row.get("actor_role")
    if actor is not None or model_s:
        role_key = _resolve_role_key(actor, registry=registry, fallback="unknown")
        bucket = _bucket_for(
            buckets,
            role_key,
            role_id=str(actor) if actor is not None else None,
        )
        bucket.event_count += 1
        if model_s:
            bucket.model_counts[model_s] = bucket.model_counts.get(model_s, 0) + 1


def _finalize_role_bucket(bucket: _RoleBucket) -> dict[str, Any]:
    out: dict[str, Any] = {
        "role_key": bucket.role_key,
        "event_count": bucket.event_count,
        "models": dict(sorted(bucket.model_counts.items())),
    }
    if bucket.role_id:
        out["role_id"] = bucket.role_id
    if bucket.duration_ms_samples:
        out["stage_duration_ms"] = {
            "count": len(bucket.duration_ms_samples),
            "total": bucket.duration_ms_total,
            "max": max(bucket.duration_ms_samples),
            "p95": _p95(bucket.duration_ms_samples),
        }
    if bucket.prompt_tokens_total or bucket.completion_tokens_total:
        out["token_hints"] = {
            "prompt_tokens_total": bucket.prompt_tokens_total,
            "completion_tokens_total": bucket.completion_tokens_total,
        }
    if bucket.latency_ms_samples:
        out["inference_latency_ms"] = {
            "count": len(bucket.latency_ms_samples),
            "max": max(bucket.latency_ms_samples),
            "p95": _p95(bucket.latency_ms_samples),
        }
    return out


def _finalize_preflight(preflight: _PreflightAccumulator) -> dict[str, Any] | None:
    if not preflight.samples:
        return None
    ctx: list[int] = []
    p95s: list[int] = []
    for sample in preflight.samples:
        ct = sample.get("context_tokens")
        p95 = sample.get("p95_latency_ms")
        if isinstance(ct, int):
            ctx.append(ct)
        if isinstance(p95, int):
            p95s.append(p95)
    out: dict[str, Any] = {
        "sample_count": len(preflight.samples),
        "samples": preflight.samples,
    }
    if ctx:
        out["avg_context_tokens"] = round(sum(ctx) / len(ctx), 2)
    if p95s:
        out["avg_p95_latency_ms"] = round(sum(p95s) / len(p95s), 2)
        out["max_p95_latency_ms"] = max(p95s)
    return out


def aggregate_role_telemetry_rows(
    rows: list[dict[str, Any]],
    *,
    registry: RoleRegistry | None = None,
    run_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build role telemetry summary document from ordered event rows (one or many runs)."""
    buckets: dict[str, _RoleBucket] = {}
    preflight = _PreflightAccumulator()
    for row in rows:
        accumulate_event_row(buckets, preflight, row, registry=registry)
    roles = {
        key: _finalize_role_bucket(bucket)
        for key, bucket in sorted(buckets.items(), key=lambda item: item[0])
    }
    doc: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_count": len(set(run_ids)) if run_ids else None,
        "event_count": len(rows),
        "roles": roles,
    }
    if run_ids:
        doc["runs_scanned"] = list(run_ids)
    pf = _finalize_preflight(preflight)
    if pf is not None:
        doc["preflight"] = pf
    return doc


def aggregate_recent_run_telemetry(
    store: Any,
    *,
    registry: RoleRegistry | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Batch-read recent runs and aggregate per-role telemetry."""
    run_ids = store.list_recent_run_ids(limit=limit, offset=offset, order="newest_first")
    ids = [str(rid) for rid in run_ids]
    if hasattr(store, "list_run_events_many"):
        row_map = store.list_run_events_many(ids)
        rows: list[dict[str, Any]] = []
        for rid in ids:
            rows.extend(row_map.get(rid, []))
    else:
        rows = []
        for rid in ids:
            rows.extend(store.list_run_events(rid))
    return aggregate_role_telemetry_rows(rows, registry=registry, run_ids=ids)
