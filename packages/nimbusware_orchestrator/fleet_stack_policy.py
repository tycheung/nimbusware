from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG

VALID_STACK_SURFACES = frozenset({"api", "web", "infra", "deploy", "contract"})


@dataclass(frozen=True)
class FleetStackPolicy:
    tenant_slug: str
    allowed_stacks: dict[str, str] = field(default_factory=dict)

    def restricts_stacks(self) -> bool:
        return bool(self.allowed_stacks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "allowed_stacks": dict(self.allowed_stacks),
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_stack_policies.yaml"


def normalize_allowed_stacks(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for surface, stack_id in raw.items():
        sid = str(surface).strip().lower()
        stack = str(stack_id or "").strip()
        if sid in VALID_STACK_SURFACES and stack:
            out[sid] = stack
    return out


def load_fleet_stack_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetStackPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetStackPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetStackPolicy(
            tenant_slug=slug_s,
            allowed_stacks=normalize_allowed_stacks(entry.get("allowed_stacks")),
        )
    return out


def save_fleet_stack_policies(
    policies: dict[str, FleetStackPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {"allowed_stacks": dict(p.allowed_stacks)}
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_stack_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetStackPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_stack_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetStackPolicy(tenant_slug=slug)


def apply_regulated_stack_guard(
    manifest: dict[str, Any],
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    policy = tenant_stack_policy(tenant_slug, repo_root=repo_root)
    if not policy.restricts_stacks():
        return manifest
    allowed = policy.allowed_stacks
    out = deepcopy(manifest)
    surfaces_raw = out.get("surfaces")
    surfaces = (
        [str(s).strip().lower() for s in surfaces_raw if str(s).strip()]
        if isinstance(surfaces_raw, list)
        else []
    )
    permitted_surfaces = [s for s in surfaces if s in allowed]
    if not permitted_surfaces:
        permitted_surfaces = sorted(allowed.keys())
    stacks = dict(out.get("stacks") or {}) if isinstance(out.get("stacks"), dict) else {}
    clamps: list[str] = []
    guarded_stacks: dict[str, str] = {}
    for surface in permitted_surfaces:
        permitted_stack = allowed.get(surface)
        if not permitted_stack:
            continue
        prior = stacks.get(surface)
        if prior and prior != permitted_stack:
            clamps.append(f"{surface}:{prior}->{permitted_stack}")
        guarded_stacks[surface] = permitted_stack
    out["surfaces"] = permitted_surfaces
    out["stacks"] = guarded_stacks
    if clamps:
        out["regulated_stack_guard"] = {
            "tenant_slug": policy.tenant_slug,
            "clamps": clamps,
        }
    return out
