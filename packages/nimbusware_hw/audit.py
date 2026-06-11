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
    ResourcePressureWarnEvent,
    ResourcePressureWarnPayload,
)
from nimbusware_hw.pressure import PressureLevel, sample_pressure
from nimbusware_hw.profile import HardwareProfile

if TYPE_CHECKING:
    from nimbusware_store.protocol import EventStore


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


_WARN_LEVELS: frozenset[PressureLevel] = frozenset({"warn", "throttle", "block"})
_DEFAULT_COOLDOWN_SEC = 60.0


def _last_pressure_warn_at(store: EventStore, run_id: UUID) -> datetime | None:
    rows = store.list_run_events(str(run_id))
    for row in reversed(rows):
        if row.get("event_type") != EventType.RESOURCE_PRESSURE_WARN.value:
            continue
        occurred = row.get("occurred_at")
        if isinstance(occurred, datetime):
            return occurred
    return None


def maybe_append_resource_pressure_warn(
    store: EventStore,
    *,
    run_id: UUID,
    governor: Any | None = None,
    hook: str | None = None,
    cooldown_seconds: float = _DEFAULT_COOLDOWN_SEC,
    level: PressureLevel | None = None,
    details: dict[str, Any] | None = None,
) -> int | None:
    """Rate-limited mid-run ``resource.pressure.warn`` when governor sampling is elevated."""
    if level is None:
        level, sampled = sample_pressure(governor)
        details = sampled if isinstance(sampled, dict) else {}
    elif details is None:
        details = {}
    if level not in _WARN_LEVELS:
        return None
    last = _last_pressure_warn_at(store, run_id)
    now = datetime.now(timezone.utc)
    if last is not None and (now - last).total_seconds() < cooldown_seconds:
        return None
    tier = str(details.get("tier") or "") if isinstance(details, dict) else ""
    reason = details.get("reason") if isinstance(details, dict) else None
    ram_used = details.get("ram_used_pct") if isinstance(details, dict) else None
    event = ResourcePressureWarnEvent(
        event_type=EventType.RESOURCE_PRESSURE_WARN,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=now,
        payload=ResourcePressureWarnPayload(
            pressure_level=level,
            pressure_reason=str(reason) if reason is not None else None,
            hardware_tier=tier or None,
            ram_used_pct=float(ram_used) if ram_used is not None else None,
            hook=hook,
        ),
    )
    return store.append(event)
