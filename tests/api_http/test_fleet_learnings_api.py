from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from env.edition import ENTERPRISE_EDITION, ENV_EDITION
from iam.constants import API_KEY_HEADER
from orchestrator.improvement.diagnose_learn import learnings_dir


def test_fleet_learnings_search_enterprise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from api.app import app

    ws = tmp_path / "workspace"
    ws.mkdir()
    (learnings_dir(ws) / "retry-batch.md").write_text(
        "# Retry batch\nUse smaller SQL batch on timeout",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}

        create = client.post(
            "/v1/projects",
            json={"name": "Acme app", "workspace_path": str(ws), "template": "attach"},
            headers=headers,
        )
        assert create.status_code == 200

        r = client.get(
            "/v1/enterprise/fleet-learnings/search",
            params={"q": "sql batch"},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["hit_count"] >= 1
        assert body["hits"][0]["learning_id"] == "retry-batch"
