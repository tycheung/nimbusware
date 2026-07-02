from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

VALID_STACK_SURFACES = frozenset({"api", "web", "infra", "deploy", "contract"})

_YAML = "fleet_stack_policies.yaml"


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


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetStackPolicy:
    return FleetStackPolicy(
        tenant_slug=slug,
        allowed_stacks=normalize_allowed_stacks(entry.get("allowed_stacks")),
    )


def _serialize_entry(policy: FleetStackPolicy) -> dict[str, Any]:
    return {"allowed_stacks": dict(policy.allowed_stacks)}


def load_fleet_stack_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetStackPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_stack_policies(
    policies: dict[str, FleetStackPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_stack_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetStackPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_stack_policies,
        FleetStackPolicy,
        repo_root=repo_root,
    )


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
