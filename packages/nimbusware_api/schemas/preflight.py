"""Fleet preflight history response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PreflightHistoryEntry(BaseModel):
    """One run's latest preflight projection (same shape as timeline ``preflight``)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    preflight: dict[str, Any] | None = None


class PreflightMetricsExportFilters(BaseModel):
    """Filters echoed in ``metrics_export`` for external consumers."""

    model_config = ConfigDict(extra="forbid")

    workflow_profile: str | None = None
    workflow_profile_prefix: str | None = None
    created_after: str | None = None
    created_before: str | None = None
    has_escalation: bool | None = None
    status: str | None = None


class PreflightMetricsExport(BaseModel):
    """Stable export payload for fleet preflight SLIs."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    export_schema_version: int = 1
    window_limit: int
    window_offset: int
    order: Literal["newest_first", "oldest_first"] = "newest_first"
    window_total_matching_runs: int
    runs_scanned: int
    has_more: bool
    runs_with_preflight: int
    runs_without_preflight: int
    runs_with_p95_latency: int
    runs_with_multisample_preflight: int
    runs_with_checks_passed: int
    distinct_validated_model_id_count: int
    avg_p95_latency_ms: float | None = None
    max_p95_latency_ms: int | None = None
    preflight_coverage_ratio: float | None = None
    p95_latency_coverage_ratio: float | None = None
    export_window_consistent: bool = True
    filters: PreflightMetricsExportFilters


class PreflightHistoryResponse(BaseModel):
    """``GET /v1/preflight-history`` — bounded fleet aggregation."""

    model_config = ConfigDict(extra="forbid")

    entries: list[PreflightHistoryEntry]
    limit: int
    total: int
    has_more: bool
    order: Literal["newest_first", "oldest_first"] = "newest_first"
    runs_with_preflight: int = 0
    runs_without_preflight: int = 0
    runs_with_p95_latency: int = 0
    avg_p95_latency_ms: float | None = None
    max_p95_latency_ms: int | None = None
    preflight_coverage_ratio: float | None = None
    p95_latency_coverage_ratio: float | None = None
    runs_with_multisample_preflight: int = 0
    runs_with_checks_passed: int = 0
    distinct_validated_model_id_count: int = 0
    metrics_export: PreflightMetricsExport | None = None
