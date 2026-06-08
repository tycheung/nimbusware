from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from nimbusware_maker.push_subscriptions import (
    list_push_subscriptions,
    push_send_enabled,
    unregister_push_subscription,
    vapid_private_key,
    vapid_subject,
)

_log = logging.getLogger(__name__)


def _payload_json(*, title: str, body: str, run_id: str, event_type: str) -> str:
    return json.dumps(
        {
            "title": title,
            "body": body,
            "run_id": run_id,
            "event_type": event_type,
        },
    )


def send_campaign_push(
    run_id: UUID | str,
    *,
    event_type: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    """Best-effort Web Push for campaign milestones; never raises."""
    if not push_send_enabled():
        return {"status": "skipped", "reason": "push_send_not_configured"}

    run_key = str(run_id)
    subscriptions = list_push_subscriptions(run_id=run_key)
    if not subscriptions:
        subscriptions = list_push_subscriptions()
    if not subscriptions:
        return {"status": "skipped", "reason": "no_subscriptions"}

    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-untyped]
    except ImportError:
        return {"status": "skipped", "reason": "pywebpush_not_installed"}

    data = _payload_json(title=title, body=body, run_id=run_key, event_type=event_type)
    sent = 0
    pruned = 0
    errors: list[str] = []
    for sub in subscriptions:
        endpoint = str(sub.get("endpoint") or "").strip()
        if not endpoint:
            continue
        try:
            webpush(
                subscription_info=sub,
                data=data,
                vapid_private_key=vapid_private_key(),
                vapid_claims={"sub": vapid_subject()},
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                unregister_push_subscription(endpoint)
                pruned += 1
            else:
                errors.append(str(exc)[:200])
        except Exception as exc:  # noqa: BLE001 — best-effort notify
            errors.append(str(exc)[:200])

    if sent:
        return {"status": "sent", "sent": sent, "pruned": pruned, "errors": errors[:3]}
    return {
        "status": "error" if errors else "skipped",
        "pruned": pruned,
        "errors": errors[:3],
    }


def notify_campaign_created(run_id: UUID) -> dict[str, Any]:
    return send_campaign_push(
        run_id,
        event_type="campaign.created",
        title="Campaign started",
        body="Your Nimbusware campaign is running.",
    )


def notify_campaign_completed(run_id: UUID, *, summary: str = "") -> dict[str, Any]:
    body = summary.strip() or "Campaign finished successfully."
    return send_campaign_push(
        run_id,
        event_type="campaign.completed",
        title="Campaign complete",
        body=body[:240],
    )


def notify_campaign_failed(run_id: UUID, *, summary: str = "") -> dict[str, Any]:
    body = summary.strip() or "Campaign failed or was stopped."
    return send_campaign_push(
        run_id,
        event_type="campaign.failed",
        title="Campaign stopped",
        body=body[:240],
    )


def notify_campaign_paused(run_id: UUID, *, reason: str = "") -> dict[str, Any]:
    body = reason.strip() or "Campaign paused."
    return send_campaign_push(
        run_id,
        event_type="campaign.paused",
        title="Campaign paused",
        body=body[:240],
    )
