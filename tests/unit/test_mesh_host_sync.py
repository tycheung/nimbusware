from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
from compute.mesh_event_replay import (
    baseline_event_ids,
    collect_replay_events,
    replay_events_to_store,
)
from compute.mesh_host_sync import (
    absorb_completed_mesh_units,
    critic_gate_fail_from_mesh,
    local_stage_names,
    remote_stage_names,
    wait_for_mesh_units,
    writer_stage_result_from_mesh,
)
from compute.mesh_workspace_merge import (
    apply_workspace_files,
    diff_workspace_files,
    workspace_file_digests,
)
from compute.work_unit import InMemoryWorkUnitQueue, set_work_unit_queue
from orchestrator.collab.scheduler import MeshScheduler
from orchestrator.pipeline import make_dev_orchestrator


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


def test_replay_events_to_host_store() -> None:
    orch, store = make_dev_orchestrator()
    run_id = orch.create_run("micro_slice")
    baseline = baseline_event_ids(store, run_id)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="implementation", attempt=1),
        ),
    )
    replayed = collect_replay_events(store, run_id, baseline)

    host, host_store = make_dev_orchestrator()
    host_run_id = host.create_run("micro_slice")
    for event in replayed:
        event["run_id"] = str(host_run_id)
    assert replay_events_to_store(host_store, host_run_id, replayed) == 1
    names = [
        (r.get("payload") or {}).get("stage_name")
        for r in host_store.list_run_events(str(host_run_id))
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "implementation" in names


def test_absorb_completed_mesh_units_replays_events(tmp_path) -> None:
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    orch, store = make_dev_orchestrator()
    run_id = orch.create_run("micro_slice")
    rec = queue.enqueue(run_id=run_id, stage_name="implementation")
    queue.dequeue(node_id=uuid4())
    queue.complete(
        rec.work_unit_id,
        status="ok",
        result={
            "executed": True,
            "verifier_exit_code": 0,
            "verifier_log": "ok",
            "replay_events": [
                {
                    "event_id": str(uuid4()),
                    "run_id": str(run_id),
                    "event_type": EventType.STAGE_STARTED.value,
                    "event_version": 1,
                    "occurred_at": "2026-01-01T00:00:00Z",
                    "payload": {"stage_name": "implementation", "attempt": 1},
                    "metadata": {},
                }
            ],
        },
    )
    stats = absorb_completed_mesh_units(store, run_id, ["implementation"], host_workspace=tmp_path)
    assert stats["events_replayed"] == 1


def test_workspace_patch_merge_on_host(tmp_path) -> None:
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "app.py").write_text("v1\n", encoding="utf-8")
    before = workspace_file_digests(ws)
    (ws / "app.py").write_text("v2\n", encoding="utf-8")
    after = workspace_file_digests(ws)
    patch = diff_workspace_files(before, after, ws)
    assert patch["app.py"].replace("\r\n", "\n") == "v2\n"

    host = tmp_path / "host"
    host.mkdir()
    (host / "app.py").write_text("v1\n", encoding="utf-8")
    merged = apply_workspace_files(host, patch)
    assert merged == ["app.py"]
    assert "v2" in (host / "app.py").read_text(encoding="utf-8")
    assert "v1" not in (host / "app.py").read_text(encoding="utf-8")
