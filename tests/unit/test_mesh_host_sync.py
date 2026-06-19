from uuid import uuid4

from nimbusware_compute.mesh_host_sync import (
    critic_gate_fail_from_mesh,
    local_stage_names,
    remote_stage_names,
    wait_for_mesh_units,
    writer_stage_result_from_mesh,
)
from nimbusware_compute.work_unit import InMemoryWorkUnitQueue, set_work_unit_queue
from nimbusware_orchestrator.mesh_scheduler import MeshScheduler


def test_remote_and_local_stage_names() -> None:
    n1 = uuid4()
    assignments = {"implementation": n1, "test_writer": None}
    assert remote_stage_names(assignments) == {"implementation"}
    assert local_stage_names(assignments) == {"test_writer"}


def test_wait_for_mesh_units_completes() -> None:
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    run_id = uuid4()
    rec = queue.enqueue(run_id=run_id, stage_name="security_critique")
    queue.dequeue(node_id=uuid4())
    assert not wait_for_mesh_units(run_id, ["security_critique"], timeout_seconds=0.5)
    queue.complete(rec.work_unit_id, status="ok", result={"gate_fail": False})
    assert wait_for_mesh_units(run_id, ["security_critique"], timeout_seconds=2.0)


def test_critic_gate_fail_from_mesh() -> None:
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    run_id = uuid4()
    rec = queue.enqueue(run_id=run_id, stage_name="security_critique")
    queue.dequeue(node_id=uuid4())
    queue.complete(rec.work_unit_id, status="ok", result={"gate_fail": True, "executed": True})
    assert critic_gate_fail_from_mesh(run_id, "security_critique") is True


def test_writer_stage_result_from_mesh_ok() -> None:
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    run_id = uuid4()
    rec = queue.enqueue(run_id=run_id, stage_name="implementation")
    queue.dequeue(node_id=uuid4())
    queue.complete(
        rec.work_unit_id,
        status="ok",
        result={"executed": True, "verifier_exit_code": 0, "verifier_log": "remote"},
    )
    out = writer_stage_result_from_mesh(run_id, "implementation")
    assert out.verifier_exit_code == 0
    assert "remote" in out.verifier_log


def test_mesh_scheduler_auto_optimize_assigns_remote() -> None:
    sched = MeshScheduler(mode="auto_optimize")
    sid = uuid4()
    n1 = uuid4()
    sched.register_session_nodes(sid, [n1])
    out = sched.assign(
        parallel_group="writers",
        stage_names=["implementation"],
        session_id=sid,
    )
    assert out["implementation"] == n1
