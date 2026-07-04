from __future__ import annotations

from orchestrator._pipeline._helpers import (
    UUID,
    Any,
    Path,
    RunDispatchTask,
    get_run_queue,
    run_dispatch_enabled,
    task_payload_workspace,
)
from orchestrator._pipeline.protocol_hosts import LifecycleVerifyHost


class LifecycleVerifyMixin:
    def execute_writer_verifier_pass(
        self: LifecycleVerifyHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> None:
        self.execute_micro_slice_pass(run_id, workspace=workspace)
        self._run_writer_group_dispatch(run_id, workspace=workspace)
        self._run_post_writer_critique_tail(run_id)

    def _run_post_writer_critique_tail(
        self: LifecycleVerifyHost,
        run_id: UUID,
    ) -> None:
        from env.env_flags import env_force_on
        from orchestrator.llm.post_verify_role_bindings import (
            emit_stub_implementation_critique_panel,
        )

        eff = self._effective_universal_critique_for_run(run_id)
        if not (eff.impl_stub or env_force_on("NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS")):
            return
        emit_stub_implementation_critique_panel(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
        )

    def dispatch_or_run_verify(
        self: LifecycleVerifyHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> str:
        if not run_dispatch_enabled():
            self.execute_writer_verifier_pass(run_id, workspace=workspace)
            return "sync"
        payload: dict[str, Any] = {}
        if workspace is not None:
            payload["workspace"] = str(workspace)
        get_run_queue().enqueue(
            RunDispatchTask(run_id=str(run_id), step="verify", payload=payload),
        )
        return "queued"

    def process_verify_dispatch_task(self: LifecycleVerifyHost, task: RunDispatchTask) -> None:
        ws_raw = task_payload_workspace(task.payload)
        ws = Path(ws_raw) if ws_raw else None
        self.execute_writer_verifier_pass(UUID(task.run_id), workspace=ws)
