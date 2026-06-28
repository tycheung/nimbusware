from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG

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


@dataclass(frozen=True)
class FleetDiscoveryPolicy:
    tenant_slug: str
    discovery_required_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "discovery_required_fields": list(self.discovery_required_fields),
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_discovery_policies.yaml"


def _normalize_fields(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        field_id = str(item).strip()
        if field_id and field_id in VALID_DISCOVERY_FIELD_IDS and field_id not in out:
            out.append(field_id)
    return tuple(out)


def load_fleet_discovery_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDiscoveryPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetDiscoveryPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetDiscoveryPolicy(
            tenant_slug=slug_s,
            discovery_required_fields=_normalize_fields(entry.get("discovery_required_fields")),
        )
    return out


def save_fleet_discovery_policies(
    policies: dict[str, FleetDiscoveryPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {"discovery_required_fields": list(p.discovery_required_fields)}
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_discovery_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDiscoveryPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_discovery_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetDiscoveryPolicy(tenant_slug=slug)
