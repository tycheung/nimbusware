from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG


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


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_slice_policies.yaml"


def load_fleet_slice_policies(repo_root: Path | None = None) -> dict[str, FleetSlicePolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetSlicePolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetSlicePolicy(
            tenant_slug=slug_s,
            slice_budget_preset=str(entry.get("slice_budget_preset") or "standard"),
            max_files=max(1, int(entry.get("max_files") or 3)),
            max_loc=max(1, int(entry.get("max_loc") or 120)),
            require_unanimous_gate=bool(entry.get("require_unanimous_gate", True)),
        )
    return out


def save_fleet_slice_policies(
    policies: dict[str, FleetSlicePolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {
            "slice_budget_preset": p.slice_budget_preset,
            "max_files": p.max_files,
            "max_loc": p.max_loc,
            "require_unanimous_gate": p.require_unanimous_gate,
        }
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_slice_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetSlicePolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_slice_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetSlicePolicy(tenant_slug=slug)
