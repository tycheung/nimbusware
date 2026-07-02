from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

_YAML = "fleet_commit_policies.yaml"


@dataclass(frozen=True)
class FleetCommitPolicy:
    tenant_slug: str
    require_auto_commit: bool = False
    message_regex: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "require_auto_commit": self.require_auto_commit,
            "message_regex": self.message_regex,
        }


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetCommitPolicy:
    return FleetCommitPolicy(
        tenant_slug=slug,
        require_auto_commit=bool(entry.get("require_auto_commit", False)),
        message_regex=str(entry.get("message_regex") or ""),
    )


def _serialize_entry(policy: FleetCommitPolicy) -> dict[str, Any]:
    return {
        "require_auto_commit": policy.require_auto_commit,
        "message_regex": policy.message_regex,
    }


def load_fleet_commit_policies(repo_root: Path | None = None) -> dict[str, FleetCommitPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_commit_policies(
    policies: dict[str, FleetCommitPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_commit_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetCommitPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_commit_policies,
        FleetCommitPolicy,
        repo_root=repo_root,
    )
