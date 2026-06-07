from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

from .env import journey_env_summary


@dataclass
class JourneyClient:
    client: TestClient
    admin_headers: dict[str, str] = field(
        default_factory=lambda: {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
    )
    run_id: str | None = None
    project_id: str | None = None
    workspace_path: Path | None = None

    def attach_project(
        self,
        workspace: Path,
        *,
        name: str | None = None,
        template: str = "attach",
    ) -> dict[str, Any]:
        self.workspace_path = workspace.resolve()
        body = {
            "name": name or f"journey-{uuid4().hex[:8]}",
            "workspace_path": str(self.workspace_path),
            "template": template,
        }
        resp = self.client.post("/v1/projects", json=body, headers=self.admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        self.project_id = str(data["project_id"])
        return data

    def start_micro_slice_run(self, *, business_prompt: str = "Small app") -> dict[str, Any]:
        assert self.project_id, "attach_project first"
        resp = self.client.post(
            "/v1/runs",
            json={
                "workflow_profile": "micro_slice",
                "project_id": self.project_id,
                "requirements": {"business_prompt": business_prompt},
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        self.run_id = str(data["run_id"])
        return data

    def start_run(
        self,
        workflow_profile: str,
        *,
        business_prompt: str = "Journey run",
    ) -> dict[str, Any]:
        assert self.project_id, "attach_project first"
        resp = self.client.post(
            "/v1/runs",
            json={
                "workflow_profile": workflow_profile,
                "project_id": self.project_id,
                "requirements": {"business_prompt": business_prompt},
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        self.run_id = str(data["run_id"])
        return data

    def start_default_run(self) -> dict[str, Any]:
        resp = self.client.post("/v1/runs", json={"workflow_profile": "default"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        self.run_id = str(data["run_id"])
        return data

    def get_pending(self) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.get(f"/v1/runs/{self.run_id}/maker/pending")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def approve_plan(self) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(f"/v1/runs/{self.run_id}/maker/plan/approve")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def prepare_slice(self) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(f"/v1/runs/{self.run_id}/maker/slices/prepare")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def apply_slice(self, slice_id: str) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(
            f"/v1/runs/{self.run_id}/maker/slices/apply",
            json={"slice_id": slice_id},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def skip_slice(self, slice_id: str) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(
            f"/v1/runs/{self.run_id}/maker/slices/skip",
            json={"slice_id": slice_id},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def revert_workspace(self) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(f"/v1/runs/{self.run_id}/workspace/revert")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def lifecycle_slice(self) -> dict[str, Any]:
        assert self.run_id
        resp = self.client.post(f"/v1/runs/{self.run_id}/lifecycle/slice")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def timeline(self) -> list[dict[str, Any]]:
        assert self.run_id
        resp = self.client.get(f"/v1/runs/{self.run_id}/timeline")
        assert resp.status_code == 200, resp.text
        return list(resp.json().get("events") or [])

    def wait_for_event(
        self,
        event_type: str,
        *,
        timeout_sec: float = 5.0,
        poll_interval_sec: float = 0.1,
    ) -> None:
        assert self.run_id
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            types = [str(ev.get("event_type") or "") for ev in self.timeline()]
            if event_type in types:
                return
            time.sleep(poll_interval_sec)
        tail = [str(ev.get("event_type") or "") for ev in self.timeline()][-10:]
        raise TimeoutError(
            f"run_id={self.run_id} missing event_type={event_type!r}; "
            f"last_10_event_types={tail!r}; {journey_env_summary()}"
        )

    def diagnostic_context(self) -> str:
        types = [str(ev.get("event_type") or "") for ev in self.timeline()] if self.run_id else []
        return (
            f"run_id={self.run_id} project_id={self.project_id} "
            f"workspace={self.workspace_path} last_10_event_types={types[-10:]!r} "
            f"{journey_env_summary()}"
        )
