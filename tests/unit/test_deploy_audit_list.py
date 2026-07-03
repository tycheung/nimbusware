from __future__ import annotations

import json
from pathlib import Path

from maker.deploy.credential_vault import (
    append_deploy_audit_event,
    list_deploy_audit_events,
)


def test_list_deploy_audit_events_filters_by_run_id(tmp_path: Path) -> None:
    audit = tmp_path / ".nimbusware" / "platform" / "deploy_audit.jsonl"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "\n".join(
            [
                json.dumps({"event": "deploy.apply", "run_id": "a", "occurred_at": "t1"}),
                json.dumps({"event": "deploy.smoke", "run_id": "b", "occurred_at": "t2"}),
                json.dumps({"event": "deploy.rollback", "run_id": "a", "occurred_at": "t3"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows = list_deploy_audit_events(run_id="a", repo_root=tmp_path)
    assert len(rows) == 2
    assert all(r["run_id"] == "a" for r in rows)


def test_list_deploy_audit_events_empty_when_missing(tmp_path: Path) -> None:
    assert list_deploy_audit_events(repo_root=tmp_path) == []


def test_append_then_list_round_trip(tmp_path: Path) -> None:
    append_deploy_audit_event(
        "deploy.credentials.updated",
        user_id="user-1",
        run_id="run-1",
        tenant_slug="acme",
        deploy_target="aws-ecs",
        detail="saved labels",
        repo_root=tmp_path,
    )
    rows = list_deploy_audit_events(run_id="run-1", repo_root=tmp_path)
    assert len(rows) == 1
    assert rows[0]["event"] == "deploy.credentials.updated"
    assert rows[0]["user_ref"]
    assert rows[0]["detail"] == "saved labels"
