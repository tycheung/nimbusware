from __future__ import annotations

from nimbusware_projections.builders.pressure_headline import (
    latest_resource_pressure_from_events,
    pressure_headline,
)


def test_pressure_headline_includes_reason() -> None:
    text = pressure_headline("block", {"pressure_reason": "ram_over_cap"})
    assert "block" in text.lower() or "blocking" in text.lower()
    assert "ram_over_cap" in text


def test_latest_resource_pressure_ignores_ok() -> None:
    events = [
        {
            "event_type": "hardware.profile.detected",
            "payload": {"pressure_level": "ok"},
        },
        {
            "event_type": "hardware.profile.detected",
            "payload": {"pressure_level": "warn", "pressure_reason": "ram_at_cap"},
        },
    ]
    row = latest_resource_pressure_from_events(events)
    assert row is not None
    assert row["level"] == "warn"
