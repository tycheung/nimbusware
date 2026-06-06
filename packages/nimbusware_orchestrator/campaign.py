"""Campaign entity helpers (campaign_id == run_id initially)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.backlog import CampaignPolicy
from agent_core.models.events_payloads import CampaignCreatedPayload, CampaignPolicyPayload
from agent_core.models.events_records import CampaignCreatedEvent
from agent_core.read.campaign import campaign_effective_from_rows, campaign_enabled_for_run
from nimbusware_orchestrator.workflow_campaign import campaign_policy_from_blocks

__all__ = [
    "CampaignDriverState",
    "campaign_effective_from_rows",
    "campaign_enabled_for_run",
    "campaign_policy_from_rows",
    "emit_campaign_created",
    "campaign_policy_from_workflow",
]


class CampaignDriverState(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    MAINTENANCE = "maintenance"
    ASSESSING = "assessing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


def campaign_policy_from_rows(rows: list[dict[str, Any]]) -> CampaignPolicy | None:
    ce = campaign_effective_from_rows(rows)
    if not isinstance(ce, dict):
        return None
    raw = ce.get("policy")
    if not isinstance(raw, dict):
        return None
    return CampaignPolicy.model_validate(raw)


def emit_campaign_created(
    store: Any,
    run_id: UUID,
    *,
    workflow_profile: str,
    policy: CampaignPolicy,
    correlation_id: UUID | None = None,
) -> None:
    policy_payload = CampaignPolicyPayload.model_validate(policy.model_dump(mode="json"))
    store.append(
        CampaignCreatedEvent(
            event_type=EventType.CAMPAIGN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            payload=CampaignCreatedPayload(
                campaign_id=str(run_id),
                workflow_profile=workflow_profile,
                policy=policy_payload,
            ),
        ),
    )


def campaign_policy_from_workflow(
    repo_root: Any,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
    autonomous: bool | None = None,
) -> CampaignPolicy:
    from pathlib import Path

    from nimbusware_orchestrator.workflow_campaign import (
        parse_backlog_workflow_block,
        parse_campaign_workflow_block,
        parse_completion_workflow_block,
        parse_maintenance_workflow_block,
    )

    root = Path(repo_root)
    return campaign_policy_from_blocks(
        parse_campaign_workflow_block(
            root, workflow_profile, config_materializer=config_materializer
        ),
        parse_backlog_workflow_block(
            root, workflow_profile, config_materializer=config_materializer
        ),
        parse_maintenance_workflow_block(
            root, workflow_profile, config_materializer=config_materializer
        ),
        parse_completion_workflow_block(
            root, workflow_profile, config_materializer=config_materializer
        ),
        autonomous=autonomous,
    )
