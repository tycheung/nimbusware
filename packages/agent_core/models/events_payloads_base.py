from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from agent_core.models.events_foundation import RoleId, Severity


class BasePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
        populate_by_name=True,
    )


FINDING_FIX_STRICTNESS_CONTEXT_KEY = "finding_fix_strictness"

_SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.BLOCKER,
)


def _severity_rank(severity: Severity) -> int:
    return _SEVERITY_ORDER.index(severity)


class FindingFixStrictnessSettings(BasePayload):
    """Two-axis policy for when `FindingCreatedPayload` must include `required_fixes`.

    Primary (floor): all severities **at or above** `minimum_severity_requiring_fixes` in the
    ladder LOW < MEDIUM < HIGH < BLOCKER require fixes.

    Secondary: when `also_require_fixes_for_low_severity` is True, **LOW** findings also require
    fixes even if the primary floor is above LOW (e.g. floor MEDIUM still mandates fixes for LOW).
    """

    minimum_severity_requiring_fixes: Severity = Severity.MEDIUM
    also_require_fixes_for_low_severity: bool = False


DEFAULT_FINDING_FIX_STRICTNESS = FindingFixStrictnessSettings()


class NetworkEgressPolicySnapshot(BasePayload):
    """Frozen ``policy_snapshot.network_egress`` allowlist snapshot.

    Layer merge is orchestration's job; this model validates the merged shape only.
    """

    scraper_role_allowlist: list[RoleId] = Field(default_factory=list)
    domain_allowlist: list[str] = Field(default_factory=list)
    budget_bytes_per_run: int | None = None

    @field_validator("budget_bytes_per_run")
    @classmethod
    def budget_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError(
                "budget_bytes_per_run must be null or a non-negative integer",
            )
        return v


class PolicySnapshotV1(BasePayload):
    finding_fix_strictness: FindingFixStrictnessSettings
    network_egress: NetworkEgressPolicySnapshot


def finding_severity_requires_fixes(
    severity: Severity,
    settings: FindingFixStrictnessSettings,
) -> bool:
    if _severity_rank(severity) >= _severity_rank(settings.minimum_severity_requiring_fixes):
        return True
    if settings.also_require_fixes_for_low_severity and severity == Severity.LOW:
        return True
    return False


def _strictness_from_validation_info(info: ValidationInfo) -> FindingFixStrictnessSettings:
    ctx = info.context or {}
    raw = ctx.get(FINDING_FIX_STRICTNESS_CONTEXT_KEY)
    if raw is None:
        return DEFAULT_FINDING_FIX_STRICTNESS
    if isinstance(raw, FindingFixStrictnessSettings):
        return raw
    if isinstance(raw, dict):
        return FindingFixStrictnessSettings.model_validate(raw)
    raise TypeError(
        f"{FINDING_FIX_STRICTNESS_CONTEXT_KEY!r} must be "
        "FindingFixStrictnessSettings or a dict, or omitted for defaults",
    )


class RequiredFixArtifact(BasePayload):
    artifact_schema_version: Literal[1] = 1
    patch_format: Literal["json_patch", "unified_diff"] = Field(alias="format")
    target_files: list[str] = Field(min_length=1)
    patch_artifact: str = Field(min_length=1)
    validation_steps: list[str] = Field(
        min_length=1,
        description="Named checks or command ids to rerun after apply",
    )
    acceptance_criteria: str = Field(
        min_length=1,
        description="Objective signal that closes the finding (e.g. test name, exit code)",
    )
