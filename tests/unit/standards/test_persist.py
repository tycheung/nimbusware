from __future__ import annotations

from uuid import uuid4

from standards.persist import (
    STANDARDS_UPDATED_STAGE,
    persist_run_standards,
    standards_profile_from_rows,
)
from standards.profile import StandardsProfile


class _Store:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, event) -> None:
        self.events.append(
            {
                "event_type": event.event_type.value,
                "payload": event.payload.model_dump(),
                "metadata": event.metadata,
            },
        )


def test_persist_run_standards_emits_event(tmp_path) -> None:
    store = _Store()
    profile = StandardsProfile(
        profile_id="default",
        facade_id="python-fastapi",
        bundle_ids=("python-agent-hygiene",),
    )
    persist_run_standards(store, uuid4(), profile, workspace=tmp_path)
    assert store.events
    assert store.events[0]["payload"]["stage_name"] == STANDARDS_UPDATED_STAGE
    overlay = tmp_path / ".nimbusware" / "standards.yaml"
    assert overlay.is_file()
    resolved = standards_profile_from_rows(store.events, workspace=tmp_path)
    assert resolved.facade_id == "python-fastapi"
