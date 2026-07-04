from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from agent_core.models.events_payloads_base import BasePayload, PolicySnapshotV1


class RunCreatedPayload(BasePayload):
    workflow_profile: str
    policy_version: str
    config_snapshot_id: str
    policy_snapshot: PolicySnapshotV1 | None = Field(
        default=None,
        description=("Frozen policy at run start; omit until orchestration supplies it."),
    )


class RunStartedPayload(BasePayload):
    started_by: str


class RunFailedPayload(BasePayload):
    reason_code: str
    message: str


class RunCompletedPayload(BasePayload):
    summary: str


class RunEscalatedPayload(BasePayload):
    actor_id: str = Field(min_length=1, description="Human or system actor identifier.")
    reason_code: str = Field(min_length=1)
    policy_snapshot_id: str | None = None
    notes: str | None = None


class ModelPreflightStartedPayload(BasePayload):
    provider: str
    base_url: str
    requested_model_id: str


class ModelPreflightPassedPayload(BasePayload):
    provider: str
    validated_model_id: str
    context_tokens: int = Field(ge=1)
    p95_latency_ms: int = Field(ge=0)
    checks_passed: list[str] = Field(default_factory=list)
    preflight_latency_sample_count: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Health endpoint multisample count when measured.",
    )
    p95_latency_source: str | None = Field(
        default=None,
        max_length=256,
        description="Short hint for how p95_latency_ms was derived (e.g. health vs json probe).",
    )
    health_latency_samples_ms: list[int] | None = Field(
        default=None,
        max_length=20,
        description=(
            "Per-sample health probe latencies in ms when multisample preflight ran. "
            "Omitted on single-sample runs."
        ),
    )

    @field_validator("health_latency_samples_ms")
    @classmethod
    def _validate_samples_non_negative(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        for s in v:
            if not isinstance(s, int) or isinstance(s, bool):
                msg = "health_latency_samples_ms entries must be int"
                raise ValueError(msg)
            if s < 0:
                msg = "health_latency_samples_ms entries must be >= 0"
                raise ValueError(msg)
        return v


class ModelPreflightFailedPayload(BasePayload):
    provider: str
    requested_model_id: str
    reason_code: str
    failed_checks: list[str] = Field(default_factory=list)
    fallback_attempted: bool = False


class ModelSelectedPrimaryPayload(BasePayload):
    provider: str
    model_id: str


class ModelSelectedFallbackPayload(BasePayload):
    provider: str
    selected_model_id: str
    reason_code: str
    original_model_id: str


class ModelBindingOverriddenPayload(BasePayload):
    agent_role: str
    provider_id: str
    provider_kind: str
    model_id: str
    binding_source: str = "model.swap"
    previous_model_id: str | None = None


class WorkloadRoleClaimedPayload(BasePayload):
    agent_role: str
    execute_on: str = "self"
    provider_id: str
    model_id: str
    claimer_user_id: str = ""


class WorkloadRoleReleasedPayload(BasePayload):
    agent_role: str
    claimer_user_id: str = ""


class PersonaShelfUpdatedPayload(BasePayload):
    """Audit record for a write through ``POST/PUT/PATCH/DELETE /v1/personas/...``.

    Distinct from per-run events: ``run_id`` on the envelope is the API caller's
    correlation, NOT a real run (the persona catalog is repo-scoped). Persists
    in the same event store so operators can reconstruct edit history from one
    source.
    """

    shelf: Literal["business_area", "development_role"]
    persona_id: str = Field(min_length=1, max_length=200)
    prev_version: int = Field(ge=0, description="0 on first create; >=1 thereafter.")
    next_version: int = Field(ge=1)
    fields_changed: list[str] = Field(
        default_factory=list,
        max_length=16,
        description=(
            "Field names mutated by the request (subset of the PersonaEntry schema). "
            "Use the sentinel value '__deleted__' to mark a DELETE."
        ),
    )
    actor: str | None = Field(default=None, max_length=200)

    @field_validator("fields_changed")
    @classmethod
    def _fields_changed_non_empty_strings(cls, v: list[str]) -> list[str]:
        for i, name in enumerate(v):
            if not isinstance(name, str) or not name:
                raise ValueError(
                    f"fields_changed[{i}] must be a non-empty string (got {name!r})",
                )
        return v

    @model_validator(mode="after")
    def _validate_version_monotonic(self) -> PersonaShelfUpdatedPayload:
        if self.next_version <= self.prev_version:
            raise ValueError(
                "persona.shelf.updated: next_version must be strictly greater than prev_version",
            )
        return self


class HardwareProfileDetectedPayload(BasePayload):
    hardware_tier: str = Field(min_length=1, max_length=32)
    tier: str = Field(min_length=1, max_length=32)
    ram_total_gb: float | None = None
    ram_available_gb: float | None = None
    platform: str = Field(default="", max_length=64)
    profile_fingerprint: str | None = Field(default=None, max_length=64)
    pressure_level: str | None = Field(default=None, max_length=16)
    pressure_reason: str | None = Field(default=None, max_length=64)


class ResourcePressureWarnPayload(BasePayload):
    pressure_level: str = Field(min_length=1, max_length=16)
    pressure_reason: str | None = Field(default=None, max_length=64)
    hardware_tier: str | None = Field(default=None, max_length=32)
    ram_used_pct: float | None = None
    hook: str | None = Field(default=None, max_length=64)


class ContextBudgetSampledPayload(BasePayload):
    provider: str = Field(default="", max_length=64)
    stage_name: str = Field(default="", max_length=128)
    tokens_in: int = Field(ge=0, default=0)
    tokens_out: int = Field(ge=0, default=0)
    cache_read: int = Field(ge=0, default=0)
    cache_write: int = Field(ge=0, default=0)


class MemoryIndexedPayload(BasePayload):
    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str = Field(min_length=8, max_length=64)
    chunks_added: int = Field(ge=0)
    chunks_skipped: int = Field(ge=0)
    embedding_mode: Literal["deterministic", "ollama"] = "deterministic"
    embedding_model_id: str = Field(min_length=1, max_length=128)
    index_dir: str | None = Field(default=None, max_length=512)
