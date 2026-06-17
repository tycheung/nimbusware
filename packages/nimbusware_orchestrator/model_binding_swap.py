from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    ModelBindingOverriddenEvent,
    ModelBindingOverriddenPayload,
    WorkloadRoleClaimedEvent,
    WorkloadRoleClaimedPayload,
    WorkloadRoleReleasedEvent,
    WorkloadRoleReleasedPayload,
)
from nimbusware_store.protocol import EventStore


def append_model_binding_override(
    store: EventStore,
    run_id: UUID,
    *,
    agent_role: str,
    provider_id: str,
    provider_kind: str,
    model_id: str,
    previous_model_id: str | None = None,
) -> dict[str, Any]:
    payload = ModelBindingOverriddenPayload(
        agent_role=agent_role,
        provider_id=provider_id,
        provider_kind=provider_kind,
        model_id=model_id,
        previous_model_id=previous_model_id,
    )
    store.append(
        ModelBindingOverriddenEvent(
            event_type=EventType.MODEL_BINDING_OVERRIDDEN,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=payload,
        ),
    )
    return payload.model_dump(mode="json")


def append_role_claim(
    store: EventStore,
    run_id: UUID,
    *,
    agent_role: str,
    provider_id: str,
    model_id: str,
    claimer_user_id: str = "",
) -> dict[str, Any]:
    payload = WorkloadRoleClaimedPayload(
        agent_role=agent_role,
        execute_on="self",
        provider_id=provider_id,
        model_id=model_id,
        claimer_user_id=claimer_user_id,
    )
    store.append(
        WorkloadRoleClaimedEvent(
            event_type=EventType.WORKLOAD_ROLE_CLAIMED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=payload,
        ),
    )
    return payload.model_dump(mode="json")


def append_role_release(
    store: EventStore,
    run_id: UUID,
    *,
    agent_role: str,
    claimer_user_id: str = "",
) -> dict[str, Any]:
    payload = WorkloadRoleReleasedPayload(
        agent_role=agent_role,
        claimer_user_id=claimer_user_id,
    )
    store.append(
        WorkloadRoleReleasedEvent(
            event_type=EventType.WORKLOAD_ROLE_RELEASED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=payload,
        ),
    )
    return payload.model_dump(mode="json")
