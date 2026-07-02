from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

_YAML = "fleet_slice_policies.yaml"


@dataclass(frozen=True)
class FleetSlicePolicy:
    tenant_slug: str
    slice_budget_preset: str = "standard"
    max_files: int = 3
    max_loc: int = 120
    require_unanimous_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "slice_budget_preset": self.slice_budget_preset,
            "max_files": self.max_files,
            "max_loc": self.max_loc,
            "require_unanimous_gate": self.require_unanimous_gate,
        }


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetSlicePolicy:
    return FleetSlicePolicy(
        tenant_slug=slug,
        slice_budget_preset=str(entry.get("slice_budget_preset") or "standard"),
        max_files=max(1, int(entry.get("max_files") or 3)),
        max_loc=max(1, int(entry.get("max_loc") or 120)),
        require_unanimous_gate=bool(entry.get("require_unanimous_gate", True)),
    )


def _serialize_entry(policy: FleetSlicePolicy) -> dict[str, Any]:
    return {
        "slice_budget_preset": policy.slice_budget_preset,
        "max_files": policy.max_files,
        "max_loc": policy.max_loc,
        "require_unanimous_gate": policy.require_unanimous_gate,
    }


def load_fleet_slice_policies(repo_root: Path | None = None) -> dict[str, FleetSlicePolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_slice_policies(
    policies: dict[str, FleetSlicePolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_slice_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetSlicePolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_slice_policies,
        FleetSlicePolicy,
        repo_root=repo_root,
    )
