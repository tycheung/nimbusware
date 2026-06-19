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


def test_mesh_pipeline_hook_enqueues_remote_units(tmp_path) -> None:
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=["implementation"],
        session_id=sid,
        workload_distribution="auto_share",
        node_ids=[n1],
        workspace=tmp_path,
    )
    queue = get_work_unit_queue()
    units = queue.list_units(run_id=run_id)
    assert len(units) == 1
    assert units[0].stage_name == "implementation"
    assert units[0].payload.get("workspace") is not None


def test_host_only_skips_enqueue() -> None:
    run_id = uuid4()
    mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=["implementation"],
        session_id=uuid4(),
        workload_distribution="host_only",
        node_ids=[uuid4()],
    )
    units = get_work_unit_queue().list_units(run_id=run_id)
    assert not units


def test_mesh_pipeline_hook_enqueues_campaign_slices() -> None:
    from nimbusware_orchestrator.mesh_pipeline_hook import mesh_assign_campaign_slices

    sid = uuid4()
    run_id = uuid4()
    n1, n2 = uuid4(), uuid4()
    mesh_assign_campaign_slices(
        run_id=run_id,
        slice_ids=["slice-a", "slice-b"],
        session_id=sid,
        workload_distribution="auto_share",
        node_ids=[n1, n2],
    )
    units = get_work_unit_queue().list_units(run_id=run_id)
    assert len(units) == 2
    assert {u.stage_name for u in units} == {"campaign.slice:slice-a", "campaign.slice:slice-b"}


def test_mesh_pipeline_hook_enqueues_parallel_critics() -> None:
    from nimbusware_orchestrator.mesh_pipeline_hook import mesh_assign_parallel_critics

    sid = uuid4()
    run_id = uuid4()
    n1, n2, n3 = uuid4(), uuid4(), uuid4()
    mesh_assign_parallel_critics(
        run_id=run_id,
        session_id=sid,
        workload_distribution="auto_share",
        node_ids=[n1, n2, n3],
    )
    units = get_work_unit_queue().list_units(run_id=run_id)
    assert len(units) == 3
    assert {u.stage_name for u in units} == {
        "security_critique",
        "performance_critique",
        "network_resilience_critique",
    }
