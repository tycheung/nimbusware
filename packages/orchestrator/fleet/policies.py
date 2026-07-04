from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar

from orchestrator.fleet.policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)
from orchestrator.profiles.autopilot_profiles import CHECKPOINT_CATALOG

T = TypeVar("T")

DEFAULT_ENTERPRISE_DEPLOY_TARGETS: tuple[str, ...] = (
    "aws-ecs",
    "aws-static-site",
    "github-actions",
)

VALID_STACK_SURFACES = frozenset({"api", "web", "infra", "deploy", "contract"})

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

DeployApprovalChain = Literal["maker_only", "session_admin", "dual_control"]
VALID_DEPLOY_APPROVAL_CHAINS = frozenset({"maker_only", "session_admin", "dual_control"})


def _tenant_policy_set(
    yaml_name: str,
    policy_cls: type[T],
    parse_entry: Callable[[str, dict[str, Any]], T],
    serialize_entry: Callable[[T], dict[str, Any]],
):
    def load(repo_root: Path | None = None) -> dict[str, T]:
        return load_tenant_policies(yaml_name, parse_entry, repo_root=repo_root)

    def save(
        policies: dict[str, T],
        *,
        repo_root: Path | None = None,
    ) -> None:
        save_tenant_policies(yaml_name, policies, serialize_entry, repo_root=repo_root)

    def tenant(
        tenant_slug: str | None,
        *,
        repo_root: Path | None = None,
    ) -> T:
        return tenant_policy(tenant_slug, load, policy_cls, repo_root=repo_root)

    return load, save, tenant


@dataclass(frozen=True)
class FleetDeployPolicy:
    tenant_slug: str
    allowed_deploy_targets: tuple[str, ...] = DEFAULT_ENTERPRISE_DEPLOY_TARGETS

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "allowed_deploy_targets": list(self.allowed_deploy_targets),
        }


def _normalize_deploy_targets(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return DEFAULT_ENTERPRISE_DEPLOY_TARGETS
    out = tuple(str(item).strip() for item in raw if str(item).strip())
    return out or DEFAULT_ENTERPRISE_DEPLOY_TARGETS


def _parse_deploy_entry(slug: str, entry: dict[str, Any]) -> FleetDeployPolicy:
    return FleetDeployPolicy(
        tenant_slug=slug,
        allowed_deploy_targets=_normalize_deploy_targets(entry.get("allowed_deploy_targets")),
    )


def _serialize_deploy_entry(policy: FleetDeployPolicy) -> dict[str, Any]:
    return {"allowed_deploy_targets": list(policy.allowed_deploy_targets)}


load_fleet_deploy_policies, save_fleet_deploy_policies, _tenant_deploy = _tenant_policy_set(
    "fleet_deploy_policies.yaml",
    FleetDeployPolicy,
    _parse_deploy_entry,
    _serialize_deploy_entry,
)


def tenant_deploy_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployPolicy:
    return _tenant_deploy(tenant_slug, repo_root=repo_root)


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


def _parse_commit_entry(slug: str, entry: dict[str, Any]) -> FleetCommitPolicy:
    return FleetCommitPolicy(
        tenant_slug=slug,
        require_auto_commit=bool(entry.get("require_auto_commit", False)),
        message_regex=str(entry.get("message_regex") or ""),
    )


def _serialize_commit_entry(policy: FleetCommitPolicy) -> dict[str, Any]:
    return {
        "require_auto_commit": policy.require_auto_commit,
        "message_regex": policy.message_regex,
    }


load_fleet_commit_policies, save_fleet_commit_policies, _tenant_commit = _tenant_policy_set(
    "fleet_commit_policies.yaml",
    FleetCommitPolicy,
    _parse_commit_entry,
    _serialize_commit_entry,
)


def tenant_commit_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetCommitPolicy:
    return _tenant_commit(tenant_slug, repo_root=repo_root)


@dataclass(frozen=True)
class FleetDeployApprovalPolicy:
    tenant_slug: str
    deploy_approval_chain: DeployApprovalChain = "maker_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "deploy_approval_chain": self.deploy_approval_chain,
        }


def _parse_deploy_approval_entry(slug: str, entry: dict[str, Any]) -> FleetDeployApprovalPolicy:
    chain = str(entry.get("deploy_approval_chain") or "maker_only").strip()
    if chain not in VALID_DEPLOY_APPROVAL_CHAINS:
        chain = "maker_only"
    return FleetDeployApprovalPolicy(
        tenant_slug=slug,
        deploy_approval_chain=chain,  # type: ignore[arg-type]
    )


def _serialize_deploy_approval_entry(policy: FleetDeployApprovalPolicy) -> dict[str, Any]:
    return {"deploy_approval_chain": policy.deploy_approval_chain}


(
    load_fleet_deploy_approval_policies,
    save_fleet_deploy_approval_policies,
    _tenant_deploy_approval,
) = _tenant_policy_set(
    "fleet_deploy_approval_policies.yaml",
    FleetDeployApprovalPolicy,
    _parse_deploy_approval_entry,
    _serialize_deploy_approval_entry,
)


def tenant_deploy_approval_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployApprovalPolicy:
    return _tenant_deploy_approval(tenant_slug, repo_root=repo_root)


@dataclass(frozen=True)
class FleetDiscoveryPolicy:
    tenant_slug: str
    discovery_required_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "discovery_required_fields": list(self.discovery_required_fields),
        }


def _normalize_discovery_fields(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        field_id = str(item).strip()
        if field_id and field_id in VALID_DISCOVERY_FIELD_IDS and field_id not in out:
            out.append(field_id)
    return tuple(out)


def _parse_discovery_entry(slug: str, entry: dict[str, Any]) -> FleetDiscoveryPolicy:
    return FleetDiscoveryPolicy(
        tenant_slug=slug,
        discovery_required_fields=_normalize_discovery_fields(
            entry.get("discovery_required_fields")
        ),
    )


def _serialize_discovery_entry(policy: FleetDiscoveryPolicy) -> dict[str, Any]:
    return {"discovery_required_fields": list(policy.discovery_required_fields)}


load_fleet_discovery_policies, save_fleet_discovery_policies, _tenant_discovery = (
    _tenant_policy_set(
        "fleet_discovery_policies.yaml",
        FleetDiscoveryPolicy,
        _parse_discovery_entry,
        _serialize_discovery_entry,
    )
)


def tenant_discovery_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDiscoveryPolicy:
    return _tenant_discovery(tenant_slug, repo_root=repo_root)


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


def _parse_slice_entry(slug: str, entry: dict[str, Any]) -> FleetSlicePolicy:
    return FleetSlicePolicy(
        tenant_slug=slug,
        slice_budget_preset=str(entry.get("slice_budget_preset") or "standard"),
        max_files=max(1, int(entry.get("max_files") or 3)),
        max_loc=max(1, int(entry.get("max_loc") or 120)),
        require_unanimous_gate=bool(entry.get("require_unanimous_gate", True)),
    )


def _serialize_slice_entry(policy: FleetSlicePolicy) -> dict[str, Any]:
    return {
        "slice_budget_preset": policy.slice_budget_preset,
        "max_files": policy.max_files,
        "max_loc": policy.max_loc,
        "require_unanimous_gate": policy.require_unanimous_gate,
    }


load_fleet_slice_policies, save_fleet_slice_policies, _tenant_slice = _tenant_policy_set(
    "fleet_slice_policies.yaml",
    FleetSlicePolicy,
    _parse_slice_entry,
    _serialize_slice_entry,
)


def tenant_slice_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetSlicePolicy:
    return _tenant_slice(tenant_slug, repo_root=repo_root)


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


def _parse_stack_entry(slug: str, entry: dict[str, Any]) -> FleetStackPolicy:
    return FleetStackPolicy(
        tenant_slug=slug,
        allowed_stacks=normalize_allowed_stacks(entry.get("allowed_stacks")),
    )


def _serialize_stack_entry(policy: FleetStackPolicy) -> dict[str, Any]:
    return {"allowed_stacks": dict(policy.allowed_stacks)}


load_fleet_stack_policies, save_fleet_stack_policies, _tenant_stack = _tenant_policy_set(
    "fleet_stack_policies.yaml",
    FleetStackPolicy,
    _parse_stack_entry,
    _serialize_stack_entry,
)


def tenant_stack_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetStackPolicy:
    return _tenant_stack(tenant_slug, repo_root=repo_root)


@dataclass(frozen=True)
class FleetAutopilotPolicy:
    tenant_slug: str
    max_autopilot_level: int = 10
    required_checkpoints: frozenset[str] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "max_autopilot_level": self.max_autopilot_level,
            "required_checkpoints": sorted(self.required_checkpoints),
        }


def _parse_autopilot_entry(slug: str, entry: dict[str, Any]) -> FleetAutopilotPolicy:
    cps_raw = entry.get("required_checkpoints")
    checkpoints = (
        frozenset(str(c) for c in cps_raw if str(c) in CHECKPOINT_CATALOG)
        if isinstance(cps_raw, list)
        else frozenset()
    )
    return FleetAutopilotPolicy(
        tenant_slug=slug,
        max_autopilot_level=max(0, min(10, int(entry.get("max_autopilot_level") or 10))),
        required_checkpoints=checkpoints,
    )


def _serialize_autopilot_entry(policy: FleetAutopilotPolicy) -> dict[str, Any]:
    return {
        "max_autopilot_level": policy.max_autopilot_level,
        "required_checkpoints": sorted(policy.required_checkpoints),
    }


load_fleet_autopilot_policies, save_fleet_autopilot_policies, _tenant_autopilot = (
    _tenant_policy_set(
        "fleet_autopilot_policies.yaml",
        FleetAutopilotPolicy,
        _parse_autopilot_entry,
        _serialize_autopilot_entry,
    )
)


def tenant_autopilot_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetAutopilotPolicy:
    return _tenant_autopilot(tenant_slug, repo_root=repo_root)


@dataclass(frozen=True)
class FleetEnforcementPolicy:
    tenant_slug: str
    min_enforcement_level: int = 0
    max_enforcement_level: int = 10
    required_enforcement_profile_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "min_enforcement_level": self.min_enforcement_level,
            "max_enforcement_level": self.max_enforcement_level,
            "required_enforcement_profile_id": self.required_enforcement_profile_id,
        }


def _parse_enforcement_entry(slug: str, entry: dict[str, Any]) -> FleetEnforcementPolicy:
    return FleetEnforcementPolicy(
        tenant_slug=slug,
        min_enforcement_level=max(0, min(10, int(entry.get("min_enforcement_level") or 0))),
        max_enforcement_level=max(0, min(10, int(entry.get("max_enforcement_level") or 10))),
        required_enforcement_profile_id=str(
            entry.get("required_enforcement_profile_id") or "",
        ).strip(),
    )


def _serialize_enforcement_entry(policy: FleetEnforcementPolicy) -> dict[str, Any]:
    return {
        "min_enforcement_level": policy.min_enforcement_level,
        "max_enforcement_level": policy.max_enforcement_level,
        "required_enforcement_profile_id": policy.required_enforcement_profile_id,
    }


load_fleet_enforcement_policies, save_fleet_enforcement_policies, _tenant_enforcement = (
    _tenant_policy_set(
        "fleet_enforcement_policies.yaml",
        FleetEnforcementPolicy,
        _parse_enforcement_entry,
        _serialize_enforcement_entry,
    )
)


def tenant_enforcement_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetEnforcementPolicy:
    return _tenant_enforcement(tenant_slug, repo_root=repo_root)


@dataclass(frozen=True)
class FleetStandardsPolicy:
    tenant_slug: str
    min_bundle_ids: tuple[str, ...] = ()
    blocked_origins: tuple[str, ...] = ("community",)
    required_facade_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "min_bundle_ids": list(self.min_bundle_ids),
            "blocked_origins": list(self.blocked_origins),
            "required_facade_id": self.required_facade_id,
        }


def _normalize_str_list(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(item).strip() for item in raw if str(item).strip())


def _parse_standards_entry(slug: str, entry: dict[str, Any]) -> FleetStandardsPolicy:
    blocked = _normalize_str_list(entry.get("blocked_origins"))
    return FleetStandardsPolicy(
        tenant_slug=slug,
        min_bundle_ids=_normalize_str_list(entry.get("min_bundle_ids")),
        blocked_origins=blocked or ("community",),
        required_facade_id=str(entry.get("required_facade_id") or "").strip(),
    )


def _serialize_standards_entry(policy: FleetStandardsPolicy) -> dict[str, Any]:
    return {
        "min_bundle_ids": list(policy.min_bundle_ids),
        "blocked_origins": list(policy.blocked_origins),
        "required_facade_id": policy.required_facade_id,
    }


load_fleet_standards_policies, save_fleet_standards_policies, _tenant_standards = (
    _tenant_policy_set(
        "fleet_standards_policies.yaml",
        FleetStandardsPolicy,
        _parse_standards_entry,
        _serialize_standards_entry,
    )
)


def tenant_standards_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetStandardsPolicy:
    return _tenant_standards(tenant_slug, repo_root=repo_root)
