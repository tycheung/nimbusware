from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

VALID_DISCOVERY_FIELD_IDS = frozenset(
    {
        "client_form",
        "backend_stack",
        "frontend_stack",
        "hosting",
        "stack_defer",
        "data_residency",
    },
)

_YAML = "fleet_discovery_policies.yaml"


@dataclass(frozen=True)
class FleetDiscoveryPolicy:
    tenant_slug: str
    discovery_required_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "discovery_required_fields": list(self.discovery_required_fields),
        }


def _normalize_fields(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        field_id = str(item).strip()
        if field_id and field_id in VALID_DISCOVERY_FIELD_IDS and field_id not in out:
            out.append(field_id)
    return tuple(out)


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetDiscoveryPolicy:
    return FleetDiscoveryPolicy(
        tenant_slug=slug,
        discovery_required_fields=_normalize_fields(entry.get("discovery_required_fields")),
    )


def _serialize_entry(policy: FleetDiscoveryPolicy) -> dict[str, Any]:
    return {"discovery_required_fields": list(policy.discovery_required_fields)}


def load_fleet_discovery_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDiscoveryPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_discovery_policies(
    policies: dict[str, FleetDiscoveryPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_discovery_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDiscoveryPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_discovery_policies,
        FleetDiscoveryPolicy,
        repo_root=repo_root,
    )
