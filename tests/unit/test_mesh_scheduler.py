from __future__ import annotations

from uuid import uuid4

from nimbusware_compute.work_unit import InMemoryWorkUnitQueue
from nimbusware_orchestrator.mesh_scheduler import MeshScheduler


def test_mesh_scheduler_host_only_assigns_host() -> None:
    sched = MeshScheduler()
    run_id = uuid4()
    session_id = uuid4()
    sched.register_session_nodes(session_id, [uuid4()])
    mapping = sched.assign(
        parallel_group="writers",
        stage_names=["implementation", "test_writer"],
        session_id=session_id,
    )
    assert mapping == {"implementation": None, "test_writer": None}
    assert sched.snapshot()["mode"] == "host_only"
    _ = run_id


def test_mesh_scheduler_set_mode() -> None:
    sched = MeshScheduler()
    sched.set_mode("auto_share")
    assert sched.mode == "auto_share"
    sched.set_mode("invalid")
    assert sched.mode == "host_only"


def test_work_unit_queue_enqueue_dequeue_complete() -> None:
    q = InMemoryWorkUnitQueue()
    run_id = uuid4()
    session_id = uuid4()
    enq = q.enqueue(
        run_id=run_id,
        session_id=session_id,
        stage_name="implementation",
        agent_role="backend_writer",
    )
    assert enq.status == "queued"
    node_id = uuid4()
    assigned = q.dequeue(session_id=session_id, node_id=node_id)
    assert assigned is not None
    assert assigned.status == "assigned"
    assert assigned.node_id == node_id
    done = q.complete(assigned.work_unit_id, status="ok", result={"events": []})
    assert done is not None
    assert done.status == "ok"
    assert done.result == {"events": []}
    # idempotent complete
    again = q.complete(assigned.work_unit_id, status="failed")
    assert again is not None
    assert again.status == "ok"
