from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG


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


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_commit_policies.yaml"


def load_fleet_commit_policies(repo_root: Path | None = None) -> dict[str, FleetCommitPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetCommitPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetCommitPolicy(
            tenant_slug=slug_s,
            require_auto_commit=bool(entry.get("require_auto_commit", False)),
            message_regex=str(entry.get("message_regex") or ""),
        )
    return out


def save_fleet_commit_policies(
    policies: dict[str, FleetCommitPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {
            "require_auto_commit": p.require_auto_commit,
            "message_regex": p.message_regex,
        }
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_commit_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetCommitPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_commit_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetCommitPolicy(tenant_slug=slug)
