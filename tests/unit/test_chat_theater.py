from __future__ import annotations

from uuid import uuid4

from agent_core.models import EventType
from compute.mesh_host_sync import (
    campaign_mesh_stage_name,
    campaign_slice_passed_from_mesh,
)
from compute.work_unit import InMemoryWorkUnitQueue, set_work_unit_queue
from projections.builders.chat_theater import (
    CHAT_THEATER_DEFAULT_CAP,
    build_chat_theater_digest,
    build_theater_messages_for_profile,
)


def test_build_chat_theater_digest_caps_messages() -> None:
    rows = [
        {
            "store_seq": i + 1,
            "event_type": EventType.STAGE_STARTED.value,
            "event_id": str(uuid4()),
            "payload": {"stage_name": f"stage-{i}"},
            "metadata": {},
        }
        for i in range(20)
    ]
    digest = build_chat_theater_digest(rows, cap=CHAT_THEATER_DEFAULT_CAP)
    assert len(digest) <= CHAT_THEATER_DEFAULT_CAP


def test_build_theater_messages_for_profile_chat() -> None:
    rows = [
        {
            "store_seq": i + 1,
            "event_type": EventType.STAGE_STARTED.value,
            "event_id": str(uuid4()),
            "payload": {"stage_name": f"stage-{i}"},
            "metadata": {},
        }
        for i in range(8)
    ]
    full = build_theater_messages_for_profile(rows, profile="full")
    chat = build_theater_messages_for_profile(rows, profile="chat", cap=3)
    assert len(full) >= len(chat)
    assert len(chat) <= 3


def test_campaign_slice_passed_from_mesh_reads_worker_result() -> None:
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    run_id = uuid4()
    slice_id = "slice-remote"
    stage = campaign_mesh_stage_name(slice_id)
    rec = queue.enqueue(
        run_id=run_id,
        stage_name=stage,
        agent_role=stage,
    )
    queue.complete(
        rec.work_unit_id,
        status="ok",
        result={"slice_passed": True, "status": "executed"},
    )
    assert campaign_slice_passed_from_mesh(run_id, slice_id) is True
