"""Append-only audit events for hardware profile lifecycle."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    HardwareProfileDetectedEvent,
    HardwareProfileDetectedPayload,
)
from nimbusware_hw.pressure import sample_pressure
from nimbusware_hw.profile import HardwareProfile

if TYPE_CHECKING:
    from hermes_store.protocol import EventStore


def _profile_fingerprint(profile: HardwareProfile) -> str:
    blob = json.dumps(profile.model_dump_public(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def append_hardware_profile_detected_event(
    store: EventStore,
    *,
    run_id: UUID,
    profile: HardwareProfile,
    governor: Any | None = None,
) -> int:
    level, details = sample_pressure(governor)
    pub = profile.model_dump_public()
    tier = str(pub.get("tier") or profile.tier or "weak")
    reason = details.get("reason") if isinstance(details, dict) else None
    event = HardwareProfileDetectedEvent(
        event_type=EventType.HARDWARE_PROFILE_DETECTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=HardwareProfileDetectedPayload(
            hardware_tier=tier,
            tier=tier,
            ram_total_gb=pub.get("ram_total_gb"),
            ram_available_gb=pub.get("ram_available_gb"),
            platform=str(pub.get("platform") or ""),
            profile_fingerprint=_profile_fingerprint(profile),
            pressure_level=level,
            pressure_reason=str(reason) if reason is not None else None,
        ),
    )
    return store.append(event)
