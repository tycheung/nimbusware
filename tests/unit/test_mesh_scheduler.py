from uuid import uuid4

from nimbusware_compute.work_unit import get_work_unit_queue
from nimbusware_orchestrator.mesh_pipeline_hook import mesh_assign_parallel_stages
from nimbusware_orchestrator.mesh_scheduler import MeshScheduler


def test_mesh_scheduler_spreads_across_nodes() -> None:
    sched = MeshScheduler(mode="auto_share")
    sid = uuid4()
    n1, n2 = uuid4(), uuid4()
    sched.register_session_nodes(sid, [n1, n2])
    out = sched.assign(
        parallel_group="writers",
        stage_names=["implementation", "test_writer"],
        session_id=sid,
    )
    assert out["implementation"] in {n1, n2}
    assert out["test_writer"] in {n1, n2}
    assert out["implementation"] != out["test_writer"]


def test_mesh_pipeline_hook_enqueues_remote_units() -> None:
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=["implementation"],
        session_id=sid,
        workload_distribution="auto_share",
        node_ids=[n1],
    )
    queue = get_work_unit_queue()
    units = [u for u in queue._units.values() if u.run_id == run_id]
    assert len(units) == 1
    assert units[0].stage_name == "implementation"


def test_host_only_skips_enqueue() -> None:
    run_id = uuid4()
    mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=["implementation"],
        session_id=uuid4(),
        workload_distribution="host_only",
        node_ids=[uuid4()],
    )
    units = [u for u in get_work_unit_queue()._units.values() if u.run_id == run_id]
    assert not units
