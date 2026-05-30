"""Project store protocol."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from nimbusware_maker.models import ProjectRecord


class ProjectStore(Protocol):
    def create(
        self,
        *,
        name: str,
        workspace_path: str,
        template: str,
        default_workflow_profile: str,
        tenant_id: UUID | None = None,
    ) -> ProjectRecord: ...

    def get(self, project_id: UUID) -> ProjectRecord | None: ...

    def list(self, *, tenant_id: UUID | None = None) -> list[ProjectRecord]: ...

    def delete(self, project_id: UUID) -> bool: ...
