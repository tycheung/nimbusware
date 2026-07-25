from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from compute.mesh_event_replay import baseline_event_ids
from compute.mesh_host_sync import remote_stage_names, wait_for_mesh_units
from compute.mesh_workspace_merge import apply_workspace_files
from compute.work_unit import InMemoryWorkUnitQueue, set_work_unit_queue


def test_mesh_helpers_work_when_compute_flag_off(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    n1 = uuid4()
    assert remote_stage_names({"implementation": n1, "test_writer": None}) == {"implementation"}
    queue = InMemoryWorkUnitQueue()
    set_work_unit_queue(queue)
    run_id = uuid4()
    rec = queue.enqueue(run_id=run_id, stage_name="security_critique")
    queue.dequeue(node_id=uuid4())
    queue.complete(rec.work_unit_id, status="ok", result={})
    assert wait_for_mesh_units(run_id, ["security_critique"], timeout_seconds=2.0)
    applied = apply_workspace_files(tmp_path, {"a.txt": "hi"})
    assert applied == ["a.txt"]


def test_mesh_helpers_raise_when_compute_broker_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    # sak423-b: host sync assignment helpers are pure under =2; event replay still refuses.
    n1 = uuid4()
    assert remote_stage_names({"implementation": n1, "test_writer": None}) == {"implementation"}
    with pytest.raises(RuntimeError, match="SwissArmyNoife compute_work"):
        baseline_event_ids(MagicMock(), uuid4())
    # Empty wait is broker-safe (no local queue).
    assert wait_for_mesh_units(uuid4(), []) is True
