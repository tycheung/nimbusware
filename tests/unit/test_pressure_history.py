from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType
from nimbusware_hw.pressure_history import pressure_history_from_event_rows


def test_pressure_history_from_event_rows() -> None:
    run_id = uuid4()
    rows = [
        {
            "event_type": EventType.RUN_CREATED.value,
            "run_id": run_id,
            "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "payload": {},
        },
        {
            "event_type": EventType.HARDWARE_PROFILE_DETECTED.value,
            "run_id": run_id,
            "occurred_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "payload": {
                "pressure_level": "warn",
                "pressure_reason": "ram_at_cap",
                "hardware_tier": "medium",
                "ram_total_gb": 16.0,
                "ram_available_gb": 4.0,
            },
        },
        {
            "event_type": EventType.HARDWARE_PROFILE_DETECTED.value,
            "run_id": run_id,
            "occurred_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
            "payload": {
                "pressure_level": "ok",
                "ram_total_gb": 16.0,
                "ram_available_gb": 12.0,
            },
        },
    ]
    hist = pressure_history_from_event_rows(rows, limit=10)
    assert len(hist) == 2
    assert hist[0]["pressure_level"] == "ok"
    assert hist[0]["ram_used_pct"] == 25.0
    assert hist[1]["pressure_level"] == "warn"
    assert hist[1]["ram_used_pct"] == 75.0
