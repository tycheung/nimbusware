from __future__ import annotations

from uuid import uuid4

from compute.work_unit import InMemoryWorkUnitQueue


def test_queued_count_filters_by_session() -> None:
    queue = InMemoryWorkUnitQueue()
    run_id = uuid4()
    session_a = uuid4()
    session_b = uuid4()
    queue.enqueue(run_id=run_id, stage_name="verify", session_id=session_a)
    queue.enqueue(run_id=run_id, stage_name="verify", session_id=session_b)
    assert queue.queued_count() == 2
    assert queue.queued_count(session_id=session_a) == 1
    assert queue.queued_count(session_id=session_b) == 1
