from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from nimbusware_orchestrator.run_dispatch import (
    RunDispatchTask,
    get_run_queue,
    run_dispatch_enabled,
    task_payload_workspace,
)
from nimbusware_store.protocol import EventStore


class _CampaignDispatchHost(Protocol):
    _store: EventStore
    _repo_root: Path

    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...

    def dispatch_or_run_campaign_tick(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> str: ...

    def process_campaign_dispatch_task(self, task: RunDispatchTask) -> None: ...


class CampaignDispatchMixin:
    def active_campaigns_for_project(self: _CampaignDispatchHost, project_id: str) -> int:
        from nimbusware_orchestrator.campaign_safety import active_campaigns_for_project

        return active_campaigns_for_project(self._store, project_id)

    def start_campaign(
        self: _CampaignDispatchHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
        autonomous: bool | None = None,
    ) -> str:
        """Emit ``campaign.created`` when missing and enqueue or run first tick."""
        from agent_core.models import EventType
        from nimbusware_orchestrator.campaign import (
            campaign_enabled_for_run,
            campaign_policy_from_workflow,
            emit_campaign_created,
        )

        rows = self._store.list_run_events(str(run_id))
        if not campaign_enabled_for_run(rows):
            msg = "campaign not enabled on run (use workflow_profile=campaign_micro_slice)"
            raise ValueError(msg)
        if not any(r.get("event_type") == EventType.CAMPAIGN_CREATED.value for r in rows):
            wf = "campaign_micro_slice"
            for row in rows:
                if row.get("event_type") != EventType.RUN_CREATED.value:
                    continue
                payload = row.get("payload")
                if isinstance(payload, dict) and payload.get("workflow_profile"):
                    wf = str(payload["workflow_profile"])
                break
            policy = campaign_policy_from_workflow(
                self._repo_root,
                wf,
                config_materializer=getattr(self, "_config_materializer", None),
                autonomous=autonomous,
            )
            emit_campaign_created(self._store, run_id, workflow_profile=wf, policy=policy)
        return self.dispatch_or_run_campaign_tick(run_id, workspace=workspace)

    def dispatch_or_run_campaign_tick(
        self: _CampaignDispatchHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> str:
        if not run_dispatch_enabled():
            self.process_campaign_dispatch_task(
                RunDispatchTask(
                    run_id=str(run_id),
                    step="campaign_tick",
                    payload={"workspace": str(workspace)} if workspace else {},
                ),
            )
            return "sync"
        payload: dict[str, Any] = {}
        if workspace is not None:
            payload["workspace"] = str(workspace)
        get_run_queue().enqueue(
            RunDispatchTask(run_id=str(run_id), step="campaign_tick", payload=payload),
        )
        return "queued"

    def process_campaign_dispatch_task(
        self: _CampaignDispatchHost,
        task: RunDispatchTask,
    ) -> None:
        from nimbusware_orchestrator.campaign_driver import campaign_driver_tick

        ws_raw = task_payload_workspace(task.payload)
        ws = Path(ws_raw) if ws_raw else None
        result = campaign_driver_tick(
            self,  # type: ignore[arg-type]
            UUID(task.run_id),
            workspace=ws,
        )
        try:
            from nimbusware_maker.web_push_notify import (
                notify_campaign_failed,
                notify_campaign_paused,
            )
            from nimbusware_orchestrator.campaign import CampaignDriverState

            run_uuid = UUID(task.run_id)
            if result.state == CampaignDriverState.PAUSED:
                notify_campaign_paused(run_uuid, reason=result.message)
            elif result.state == CampaignDriverState.FAILED:
                notify_campaign_failed(run_uuid, summary=result.message)
        except Exception:
            pass
        if result.should_continue and run_dispatch_enabled():
            payload: dict[str, Any] = {}
            if ws is not None:
                payload["workspace"] = str(ws)
            get_run_queue().enqueue(
                RunDispatchTask(
                    run_id=task.run_id,
                    step="campaign_tick",
                    payload=payload,
                ),
            )
