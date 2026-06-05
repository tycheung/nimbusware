from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from agent_core.models import EventType
from nimbusware_hw.audit import maybe_append_resource_pressure_warn
from nimbusware_hw.governor import ResourceGovernor


class _MemStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def list_run_events(self, run_id: str) -> list[dict]:
        return [r for r in self.rows if str(r.get("run_id")) == run_id]

    def append(self, event) -> int:
        self.rows.append(
            {
                "event_type": event.event_type.value,
                "run_id": event.run_id,
                "occurred_at": event.occurred_at,
                "payload": event.payload.model_dump(),
            },
        )
        return len(self.rows)


def test_maybe_append_warn_emits_once_per_cooldown(monkeypatch) -> None:
    run_id = uuid4()
    store = _MemStore()
    gov = ResourceGovernor(max_system_ram_pct=50)

    def _fake_sample(_gov):
        return "warn", {"tier": "medium", "reason": "ram_at_cap", "ram_used_pct": 82.0}

    monkeypatch.setattr("nimbusware_hw.audit.sample_pressure", _fake_sample)

    seq1 = maybe_append_resource_pressure_warn(store, run_id=run_id, governor=gov, hook="test")
    seq2 = maybe_append_resource_pressure_warn(store, run_id=run_id, governor=gov, hook="test")
    assert seq1 == 1
    assert seq2 is None
    warns = [r for r in store.rows if r["event_type"] == EventType.RESOURCE_PRESSURE_WARN.value]
    assert len(warns) == 1
    assert warns[0]["payload"]["hook"] == "test"


def test_cooldown_allows_second_warn_after_interval(monkeypatch) -> None:
    run_id = uuid4()
    store = _MemStore()
    old = datetime.now(timezone.utc) - timedelta(seconds=120)
    store.rows.append(
        {
            "event_type": EventType.RESOURCE_PRESSURE_WARN.value,
            "run_id": run_id,
            "occurred_at": old,
            "payload": {"pressure_level": "warn"},
        },
    )

    def _fake_sample(_gov):
        return "throttle", {"tier": "weak", "reason": "ram_near_cap", "ram_used_pct": 90.0}

    monkeypatch.setattr("nimbusware_hw.audit.sample_pressure", _fake_sample)

    seq = maybe_append_resource_pressure_warn(
        store,
        run_id=run_id,
        governor=ResourceGovernor(),
        cooldown_seconds=60.0,
    )
    assert seq == 2


def test_ok_pressure_skips_emit(monkeypatch) -> None:
    run_id = uuid4()
    store = _MemStore()
    monkeypatch.setattr("nimbusware_hw.audit.sample_pressure", lambda _g: ("ok", {}))
    assert maybe_append_resource_pressure_warn(store, run_id=run_id) is None
