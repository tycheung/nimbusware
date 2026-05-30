"""Maker project records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from nimbusware_iam.constants import DEFAULT_TENANT_ID

GREENFIELD_TEMPLATE = "greenfield"
ATTACH_TEMPLATE = "attach"
PROJECT_TEMPLATES = frozenset({GREENFIELD_TEMPLATE, ATTACH_TEMPLATE})


@dataclass(frozen=True)
class ProjectRecord:
    project_id: UUID
    name: str
    workspace_path: str
    template: str
    default_workflow_profile: str
    created_at: datetime
    tenant_id: UUID = DEFAULT_TENANT_ID

    def to_dict(self) -> dict[str, str]:
        return {
            "project_id": str(self.project_id),
            "name": self.name,
            "workspace_path": self.workspace_path,
            "template": self.template,
            "default_workflow_profile": self.default_workflow_profile,
            "created_at": self.created_at.isoformat(),
            "tenant_id": str(self.tenant_id),
        }
