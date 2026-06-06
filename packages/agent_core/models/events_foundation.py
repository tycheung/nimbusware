from __future__ import annotations

import math
from enum import Enum
from typing import Annotated, Any, TypeAlias
from uuid import UUID

from pydantic import (
    AfterValidator,
)

# Logical JSON contract for metadata (documentation + typing). Floats must be finite
# (RFC 8259-safe); runtime checks enforce this alongside the dict structure.
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_json_value(v) for k, v in value.items())
    return False


def _validate_envelope_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("metadata must be a dict")
    if not _is_json_value(value):
        raise ValueError(
            "metadata must be strict JSON-compatible (str keys; only None, bool, str, "
            "int, finite float, list, dict; no datetime/bytes/Decimal/set/NaN/inf)",
        )
    return value


EventMetadata = Annotated[dict[str, Any], AfterValidator(_validate_envelope_metadata)]


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKER = "BLOCKER"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_INFO = "NEEDS_INFO"


class EventType(str, Enum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_FAILED = "run.failed"
    RUN_COMPLETED = "run.completed"
    MODEL_PREFLIGHT_STARTED = "model.preflight.started"
    MODEL_PREFLIGHT_PASSED = "model.preflight.passed"
    MODEL_PREFLIGHT_FAILED = "model.preflight.failed"
    MODEL_SELECTED_PRIMARY = "model.selected.primary"
    MODEL_SELECTED_FALLBACK = "model.selected.fallback"
    STAGE_STARTED = "stage.started"
    STAGE_BLOCKED = "stage.blocked"
    STAGE_PASSED = "stage.passed"
    STAGE_FAILED = "stage.failed"
    CRITIC_VERDICT_EMITTED = "critic.verdict.emitted"
    FINDING_CREATED = "finding.created"
    FINDING_ROUTED = "finding.routed"
    FINDING_CLOSED = "finding.closed"
    GATE_DECISION_EMITTED = "gate.decision.emitted"
    RUN_ESCALATED = "run.escalated"
    GATE_OVERRIDDEN = "gate.overridden"
    PERSONA_SHELF_UPDATED = "persona.shelf.updated"
    SELF_REFINEMENT_LOOP_SIGNALLED = "self_refinement.loop.signalled"
    MEMORY_INDEXED = "memory.indexed"
    MEMORY_RETRIEVAL_EMITTED = "memory.retrieval.emitted"
    RESEARCH_BRIEF_EMITTED = "research.brief.emitted"
    RESEARCH_BRIEF_APPROVED = "research.brief.approved"
    RESEARCH_BRIEF_REJECTED = "research.brief.rejected"
    RESEARCH_PATTERN_INDEXED = "research.pattern.indexed"
    DOMAIN_CRITIC_PROPOSED = "domain.critic.proposed"
    STITCH_LICENSE_CHECKED = "stitch.license.checked"
    STITCH_DEPENDENCY_CHECKED = "stitch.dependency.checked"
    STITCH_PLAN_EMITTED = "stitch.plan.emitted"
    STITCH_APPLIED = "stitch.applied"
    STITCH_FAILED = "stitch.failed"
    HARDWARE_PROFILE_DETECTED = "hardware.profile.detected"
    RESOURCE_PRESSURE_WARN = "resource.pressure.warn"
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_COMPLETED = "campaign.completed"
    CAMPAIGN_FAILED = "campaign.failed"
    CAMPAIGN_PAUSED = "campaign.paused"
    DELIVERY_BACKLOG_GENERATED = "delivery_backlog.generated"
    DELIVERY_BACKLOG_REVISED = "delivery_backlog.revised"
    EPIC_STATUS_CHANGED = "epic.status.changed"
    SLICE_QUEUED = "slice.queued"
    SLICE_DEFERRED = "slice.deferred"
    MAINTENANCE_REFACTOR_STARTED = "maintenance.refactor.started"
    MAINTENANCE_REFACTOR_PASSED = "maintenance.refactor.passed"
    MAINTENANCE_ARCHITECTURE_STARTED = "maintenance.architecture.started"
    MAINTENANCE_ARCHITECTURE_PASSED = "maintenance.architecture.passed"
    COMPLETION_EVALUATED = "completion.evaluated"


RoleId: TypeAlias = UUID
"""Role Registry ``role_id`` on persisted events. JSON wire: UUID string."""
