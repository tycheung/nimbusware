from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

ADMIN_HEADERS = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def test_maker_approval_flow(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "maker-ws"
    ws.mkdir()
    (ws / "packages/hermes_orchestrator").mkdir(parents=True)
    (ws / "packages/hermes_orchestrator/micro_slice.py").write_text("# x\n", encoding="utf-8")
    (ws / "packages/hermes_orchestrator/slice_gate.py").write_text("# x\n", encoding="utf-8")
    project = client.post(
        "/v1/projects",
        json={"name": "Approval", "workspace_path": str(ws), "template": "attach"},
        headers=ADMIN_HEADERS,
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "micro_slice",
            "project_id": project["project_id"],
            "requirements": {"business_prompt": "Small app"},
        },
    )
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    pending = client.get(f"/v1/runs/{run_id}/maker/pending")
    assert pending.status_code == 200
    assert pending.json()["plan_approved"] is False

    approve = client.post(f"/v1/runs/{run_id}/maker/plan/approve")
    assert approve.status_code == 200

    lifecycle = client.post(f"/v1/runs/{run_id}/lifecycle/slice")
    assert lifecycle.status_code == 200
    assert lifecycle.json()["status"] in {"awaiting_approval", "all_slices_done"}

    pending2 = client.get(f"/v1/runs/{run_id}/maker/pending")
    assert pending2.json()["plan_approved"] is True

    if lifecycle.json().get("status") == "awaiting_approval":
        slice_id = lifecycle.json()["pending"]["slice_id"]
        skip = client.post(
            f"/v1/runs/{run_id}/maker/slices/skip",
            json={"slice_id": slice_id},
        )
        assert skip.status_code == 200
        assert skip.json()["status"] == "skipped"


def test_maker_apply_revert_round_trip(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_SLICE_AUTO_ADVANCE", "0")
    monkeypatch.setenv("HERMES_SLICE_IMPLEMENT", "stub")
    monkeypatch.setenv("HERMES_SKIP_PREFLIGHT", "1")
    ws = tmp_path / "revert-ws"
    ws.mkdir()
    (ws / "packages/hermes_orchestrator").mkdir(parents=True)
    (ws / "packages/hermes_orchestrator/micro_slice.py").write_text("# x\n", encoding="utf-8")
    (ws / "packages/hermes_orchestrator/slice_gate.py").write_text("# y\n", encoding="utf-8")
    project = client.post(
        "/v1/projects",
        json={"name": "Revert", "workspace_path": str(ws), "template": "attach"},
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "micro_slice",
            "project_id": project["project_id"],
            "requirements": {"business_prompt": "Tiny app"},
        },
    )
    assert run.status_code == 200
    run_id = run.json()["run_id"]
    assert client.post(f"/v1/runs/{run_id}/maker/plan/approve").status_code == 200
    prep = client.post(f"/v1/runs/{run_id}/maker/slices/prepare")
    assert prep.status_code == 200
    if prep.json().get("status") != "awaiting_approval":
        pytest.skip("no pending slice in this environment")
    pending = prep.json()["pending"]
    assert "diff_unified" in pending
    slice_id = pending["slice_id"]
    applied = client.post(
        f"/v1/runs/{run_id}/maker/slices/apply",
        json={"slice_id": slice_id},
    )
    assert applied.status_code == 200
    assert applied.json()["status"] == "applied"
    reverted = client.post(f"/v1/runs/{run_id}/workspace/revert")
    assert reverted.status_code == 200
    assert reverted.json()["status"] == "reverted"
