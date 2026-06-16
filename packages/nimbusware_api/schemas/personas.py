from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nimbusware_extensions.personas import (
    ALLOWED_PROBATION_STATUSES,
    PERSONA_ALLOWED_TOOL_MAX_CHARS,
    PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
    PERSONA_BOUNDARY_STATEMENT_MAX_CHARS,
    PERSONA_CAPABILITY_PROFILE_MAX_CHARS,
    PERSONA_INSTRUCTIONS_MAX_CHARS,
    PERSONA_SUCCESS_METRIC_MAX_CHARS,
    PERSONA_SUCCESS_METRICS_MAX_ENTRIES,
)

ProbationStatus = Literal["probation", "promoted", "shelved"]


class PersonaEntry(BaseModel):
    """One persona row on a shelf (``id`` / ``display_name`` plus optional extended fields)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    instructions: str | None = Field(
        default=None,
        max_length=PERSONA_INSTRUCTIONS_MAX_CHARS,
        description=(
            "Per-persona system-prompt / operating instructions. NFC-normalized "
            "server-side; <= 8000 chars."
        ),
    )
    capability_profile: str | None = Field(
        default=None,
        max_length=PERSONA_CAPABILITY_PROFILE_MAX_CHARS,
    )
    boundary_statement: str | None = Field(
        default=None,
        max_length=PERSONA_BOUNDARY_STATEMENT_MAX_CHARS,
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        max_length=PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
    )
    success_metrics: list[str] | None = Field(
        default=None,
        max_length=PERSONA_SUCCESS_METRICS_MAX_ENTRIES,
    )
    probation_status: ProbationStatus | None = Field(default=None)
    version: int = Field(default=1, ge=1)

    @field_validator("allowed_tools")
    @classmethod
    def _validate_allowed_tools(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"allowed_tools[{i}] must be a string")
            if len(item) > PERSONA_ALLOWED_TOOL_MAX_CHARS:
                raise ValueError(
                    f"allowed_tools[{i}] length {len(item)} exceeds cap of "
                    f"{PERSONA_ALLOWED_TOOL_MAX_CHARS}",
                )
        return v

    @field_validator("success_metrics")
    @classmethod
    def _validate_success_metrics(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"success_metrics[{i}] must be a string")
            if len(item) > PERSONA_SUCCESS_METRIC_MAX_CHARS:
                raise ValueError(
                    f"success_metrics[{i}] length {len(item)} exceeds cap of "
                    f"{PERSONA_SUCCESS_METRIC_MAX_CHARS}",
                )
        return v


class PersonaShelvesResponse(BaseModel):
    """Merged ``business_area`` + ``development_role`` entries from ``shelves.yaml``.

    Entries follow the :class:`PersonaEntry` shape but are kept as ``dict`` here so
    callers that read raw fields keep working; the route handlers run
    everything through :class:`PersonaEntry` validation before responding.
    """

    version: int | None = None
    business_area: list[dict[str, Any]] = Field(default_factory=list)
    development_role: list[dict[str, Any]] = Field(default_factory=list)


class PersonaShelfUpsertRequest(BaseModel):
    """Body for ``POST /v1/personas/{shelf}`` and ``PUT /v1/personas/{shelf}/{id}``.

    ``expected_version`` is REQUIRED for PUT (optimistic concurrency) and is
    silently ignored on POST (server assigns ``version=1`` on create).
    """

    model_config = ConfigDict(extra="forbid")

    entry: PersonaEntry
    expected_version: int | None = Field(default=None, ge=0)
    actor: str | None = Field(default=None, max_length=200)


class PersonaShelfPatchRequest(BaseModel):
    """Body for ``PATCH /v1/personas/{shelf}/{id}`` (partial update).

    Every field besides ``expected_version`` is optional; only the keys present
    in the request mutate the persona on disk.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(..., ge=1)
    display_name: str | None = Field(default=None, max_length=200)
    instructions: str | None = Field(
        default=None,
        max_length=PERSONA_INSTRUCTIONS_MAX_CHARS,
    )
    capability_profile: str | None = Field(
        default=None,
        max_length=PERSONA_CAPABILITY_PROFILE_MAX_CHARS,
    )
    boundary_statement: str | None = Field(
        default=None,
        max_length=PERSONA_BOUNDARY_STATEMENT_MAX_CHARS,
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        max_length=PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
    )
    success_metrics: list[str] | None = Field(
        default=None,
        max_length=PERSONA_SUCCESS_METRICS_MAX_ENTRIES,
    )
    probation_status: ProbationStatus | None = Field(default=None)
    actor: str | None = Field(default=None, max_length=200)

    @field_validator("allowed_tools")
    @classmethod
    def _validate_allowed_tools(cls, v: list[str] | None) -> list[str] | None:
        return PersonaEntry._validate_allowed_tools(v)

    @field_validator("success_metrics")
    @classmethod
    def _validate_success_metrics(cls, v: list[str] | None) -> list[str] | None:
        return PersonaEntry._validate_success_metrics(v)

    def mutated_fields(self) -> list[str]:
        """Return fields actually set by the caller.

        Excludes ``expected_version`` and ``actor`` since neither mutates the
        on-disk persona entry.
        """
        out: list[str] = []
        for field_name in (
            "display_name",
            "instructions",
            "capability_profile",
            "boundary_statement",
            "allowed_tools",
            "success_metrics",
            "probation_status",
        ):
            if field_name in self.model_fields_set:
                out.append(field_name)
        return out


class ProbationReliabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_id: str
    runs_evaluated: int
    avg_score: float | None = None
    below_threshold_count: int = 0
    invalid_status_count: int = 0
    decision: str
    min_eval_runs: int
    min_score: float
    max_below_ratio: float


__all__ = (
    "PersonaEntry",
    "PersonaShelvesResponse",
    "PersonaShelfUpsertRequest",
    "PersonaShelfPatchRequest",
    "ProbationReliabilityResponse",
    "ProbationStatus",
    "ALLOWED_PROBATION_STATUSES",
)
