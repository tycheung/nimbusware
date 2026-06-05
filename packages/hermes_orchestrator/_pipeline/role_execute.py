from __future__ import annotations

from pathlib import Path
from uuid import UUID

from hermes_orchestrator._pipeline.protocol_hosts import RoleExecuteHost


class RoleExecuteMixin:
    def execute_role_for_run(
        self: RoleExecuteHost,
        run_id: UUID,
        role_id: str,
        *,
        workspace: Path | None = None,
    ) -> dict[str, object]:
        from hermes_orchestrator.role_execute import dispatch_role_execute, resolve_taxonomy_key

        taxonomy_key = resolve_taxonomy_key(self._registry, role_id)
        return dispatch_role_execute(
            self,
            run_id,
            taxonomy_key,
            workspace=workspace,
        )
