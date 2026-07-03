from uuid import uuid4

from compute.work_unit import InMemoryWorkUnitQueue


def test_work_unit_terminate_restart_requeues() -> None:
    queue = InMemoryWorkUnitQueue()
    run_id = uuid4()
    original = queue.enqueue(
        run_id=run_id,
        stage_name="implementation",
        agent_role="backend_writer",
        executor_user_id="user-1",
        payload={"mesh_assignment": True},
    )
    claimed = queue.dequeue(node_id=uuid4())
    assert claimed is not None
    restarted = queue.terminate_restart(original.work_unit_id)
    assert restarted is not None
    assert restarted.work_unit_id != original.work_unit_id
    assert restarted.status == "queued"
    assert restarted.stage_name == "implementation"
    done = queue.complete(original.work_unit_id, status="cancelled")
    assert done is not None
    assert done.status == "cancelled"
