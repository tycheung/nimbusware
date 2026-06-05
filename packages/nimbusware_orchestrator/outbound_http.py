"""Policy-checked outbound HTTP using frozen ``run.created`` ``policy_snapshot``."""

from __future__ import annotations

from uuid import UUID

import httpx

from agent_core.models import EventType, RunCreatedEvent, validate_event_dict
from nimbusware_executor.fetch import egress_checked_httpx_get
from nimbusware_store.protocol import EventStore, serialized_event_from_row


def network_egress_from_run_created(
    store: EventStore,
    run_id: UUID,
) -> tuple[list[UUID], list[str]]:
    """Return ``(scraper_role_allowlist, domain_allowlist)`` from the first ``run.created`` row."""
    for row in store.list_run_events(str(run_id)):
        if row["event_type"] != EventType.RUN_CREATED.value:
            continue
        d = serialized_event_from_row(row)
        ev = validate_event_dict(d)
        if not isinstance(ev, RunCreatedEvent):
            continue
        snap = ev.payload.policy_snapshot
        if snap is None:
            msg = "run.created has no policy_snapshot; cannot enforce network egress"
            raise ValueError(msg)
        ne = snap.network_egress
        scrapers = [UUID(str(x)) for x in ne.scraper_role_allowlist]
        domains = [str(x) for x in ne.domain_allowlist]
        return scrapers, domains
    msg = f"no run.created event for run_id={run_id}"
    raise ValueError(msg)


def egress_checked_get_for_run(
    store: EventStore,
    run_id: UUID,
    url: str,
    *,
    actor_role_id: UUID,
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
    max_response_bytes: int | None = None,
) -> httpx.Response:
    """``GET`` ``url`` after resolving egress policy from the run's first ``run.created``."""
    scrapers, domains = network_egress_from_run_created(store, run_id)
    return egress_checked_httpx_get(
        url,
        actor_role_id=actor_role_id,
        scraper_role_allowlist=scrapers,
        domain_allowlist=domains,
        timeout_seconds=timeout_seconds,
        client=client,
        max_response_bytes=max_response_bytes,
    )
