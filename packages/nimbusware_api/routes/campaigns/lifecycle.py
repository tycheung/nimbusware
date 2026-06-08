"""Campaign pause / resume / cancel."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_core.models import EventType, RunFailedEvent, RunFailedPayload
from agent_core.models.events_payloads import CampaignFailedPayload, CampaignPausedPayload
from agent_core.models.events_records import CampaignFailedEvent, CampaignPausedEvent
from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem

router = APIRouter()


class CampaignActionBody(BaseModel):
    reason_code: str = Field(default="operator", max_length=64)


@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: UUID, body: CampaignActionBody, store: StoreDep) -> dict:
    rows = store.list_run_events(str(campaign_id))
    if not rows:
        raise HTTPException(status_code=404, detail=problem("run_not_found", "campaign not found"))
    store.append(
        CampaignPausedEvent(
            event_type=EventType.CAMPAIGN_PAUSED,
            event_id=uuid4(),
            run_id=campaign_id,
            occurred_at=datetime.now(timezone.utc),
            payload=CampaignPausedPayload(
                campaign_id=str(campaign_id),
                reason_code=body.reason_code,
                operator_initiated=True,
            ),
        ),
    )
    try:
        from nimbusware_maker.web_push_notify import notify_campaign_paused

        notify_campaign_paused(campaign_id, reason=body.reason_code)
    except Exception:
        pass
    return {"campaign_id": str(campaign_id), "status": "paused"}


@router.post("/campaigns/{campaign_id}/resume")
def resume_campaign(campaign_id: UUID, orch: OrchDep, store: StoreDep) -> dict:
    rows = store.list_run_events(str(campaign_id))
    if not rows:
        raise HTTPException(status_code=404, detail=problem("run_not_found", "campaign not found"))
    mode = orch.dispatch_or_run_campaign_tick(campaign_id)
    return {"campaign_id": str(campaign_id), "status": "resumed", "dispatch_mode": mode}


@router.post("/campaigns/{campaign_id}/cancel")
def cancel_campaign(campaign_id: UUID, body: CampaignActionBody, store: StoreDep) -> dict:
    rows = store.list_run_events(str(campaign_id))
    if not rows:
        raise HTTPException(status_code=404, detail=problem("run_not_found", "campaign not found"))
    now = datetime.now(timezone.utc)
    store.append(
        CampaignPausedEvent(
            event_type=EventType.CAMPAIGN_PAUSED,
            event_id=uuid4(),
            run_id=campaign_id,
            occurred_at=now,
            payload=CampaignPausedPayload(
                campaign_id=str(campaign_id),
                reason_code="cancelled",
                operator_initiated=True,
            ),
        ),
    )
    store.append(
        CampaignFailedEvent(
            event_type=EventType.CAMPAIGN_FAILED,
            event_id=uuid4(),
            run_id=campaign_id,
            occurred_at=now,
            payload=CampaignFailedPayload(
                campaign_id=str(campaign_id),
                reason_code=body.reason_code,
                summary="operator cancelled campaign",
            ),
        ),
    )
    store.append(
        RunFailedEvent(
            event_type=EventType.RUN_FAILED,
            event_id=uuid4(),
            run_id=campaign_id,
            occurred_at=now,
            payload=RunFailedPayload(reason_code="campaign_cancelled", message=body.reason_code),
        ),
    )
    try:
        from nimbusware_maker.web_push_notify import notify_campaign_failed

        notify_campaign_failed(campaign_id, summary="Campaign cancelled")
    except Exception:
        pass
    return {"campaign_id": str(campaign_id), "status": "cancelled"}
