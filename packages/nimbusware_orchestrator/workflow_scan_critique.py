from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.models import Severity
from nimbusware_env.env_flags import env_tri_state, nimbusware_use_llm_explicitly_off
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict

_SEVERITY_FLOOR = {
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
    "BLOCKER": Severity.BLOCKER,
}


def severity_for_critique_floor(floor: str) -> Severity:
    return _SEVERITY_FLOOR.get(floor.upper(), Severity.MEDIUM)


def scan_critique_gate_timeline_summary(
    events: list[dict[str, Any]],
    *,
    stage_name: str,
) -> dict[str, Any] | None:
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == stage_name:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": stage_name,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


@dataclass(frozen=True)
class ScanCritiqueBlock:
    enabled: bool = False
    stub: bool = True
    llm_enabled: bool = False
    severity_floor: str = "MEDIUM"
    backend_only: bool | None = None


def parse_scan_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    yaml_key: str,
    *,
    config_materializer: Any | None = None,
    extra_bool_defaults: dict[str, bool] | None = None,
) -> ScanCritiqueBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return ScanCritiqueBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return ScanCritiqueBlock()
    block = raw.get(yaml_key)
    if not isinstance(block, dict):
        return ScanCritiqueBlock()
    floor_raw = block.get("severity_floor", "MEDIUM")
    extras = extra_bool_defaults or {}
    backend_only = None
    if "backend_only" in extras:
        backend_only = bool(block.get("backend_only", extras["backend_only"]))
    return ScanCritiqueBlock(
        enabled=bool(block.get("enabled", False)),
        stub=bool(block.get("stub", True)),
        llm_enabled=bool(block.get("llm_enabled", False)),
        severity_floor=str(floor_raw).strip().upper() or "MEDIUM",
        backend_only=backend_only,
    )


def scan_critique_effective(block: ScanCritiqueBlock, env_key: str) -> bool:
    tri = env_tri_state(env_key)
    if tri == "off":
        return False
    if tri == "on":
        return True
    return block.enabled


def scan_critique_llm_effective(block: ScanCritiqueBlock, env_llm_key: str) -> bool:
    tri = env_tri_state(env_llm_key)
    if tri == "off":
        return False
    if tri == "on":
        return True
    if nimbusware_use_llm_explicitly_off():
        return False
    return block.llm_enabled


@dataclass(frozen=True)
class ScanCritiqueKind:
    yaml_key: str
    env_key: str
    env_llm_key: str
    extra_bool_defaults: dict[str, bool] | None = None


_SECURITY = ScanCritiqueKind(
    "security_critique", "NIMBUSWARE_SECURITY_CRITIQUE", "NIMBUSWARE_SECURITY_CRITIQUE_LLM"
)
_PERFORMANCE = ScanCritiqueKind(
    "performance_critique", "NIMBUSWARE_PERFORMANCE_CRITIQUE", "NIMBUSWARE_PERFORMANCE_CRITIQUE_LLM"
)
_NETWORK = ScanCritiqueKind(
    "network_resilience_critique",
    "NIMBUSWARE_NETWORK_RESILIENCE_CRITIQUE",
    "NIMBUSWARE_NETWORK_RESILIENCE_CRITIQUE_LLM",
    extra_bool_defaults={"backend_only": True},
)


def _parse_kind(
    kind: ScanCritiqueKind,
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> ScanCritiqueBlock:
    return parse_scan_critique_workflow_block(
        repo_root,
        workflow_profile,
        kind.yaml_key,
        config_materializer=config_materializer,
        extra_bool_defaults=kind.extra_bool_defaults,
    )


def _effective_kind(block: ScanCritiqueBlock, kind: ScanCritiqueKind) -> bool:
    return scan_critique_effective(block, kind.env_key)


def _llm_effective_kind(block: ScanCritiqueBlock, kind: ScanCritiqueKind) -> bool:
    return scan_critique_llm_effective(block, kind.env_llm_key)


SecurityCritiqueBlock = ScanCritiqueBlock
PerformanceCritiqueBlock = ScanCritiqueBlock
NetworkResilienceCritiqueBlock = ScanCritiqueBlock


def parse_security_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> SecurityCritiqueBlock:
    return _parse_kind(
        _SECURITY, repo_root, workflow_profile, config_materializer=config_materializer
    )


def security_critique_effective(block: SecurityCritiqueBlock) -> bool:
    return _effective_kind(block, _SECURITY)


def security_critique_llm_branch_effective(block: SecurityCritiqueBlock) -> bool:
    return _llm_effective_kind(block, _SECURITY)


def parse_performance_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> PerformanceCritiqueBlock:
    return _parse_kind(
        _PERFORMANCE, repo_root, workflow_profile, config_materializer=config_materializer
    )


def performance_critique_effective(block: PerformanceCritiqueBlock) -> bool:
    return _effective_kind(block, _PERFORMANCE)


def performance_critique_llm_branch_effective(block: PerformanceCritiqueBlock) -> bool:
    return _llm_effective_kind(block, _PERFORMANCE)


def parse_network_resilience_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> NetworkResilienceCritiqueBlock:
    return _parse_kind(
        _NETWORK, repo_root, workflow_profile, config_materializer=config_materializer
    )


def network_resilience_critique_effective(block: NetworkResilienceCritiqueBlock) -> bool:
    return _effective_kind(block, _NETWORK)


def network_resilience_critique_llm_branch_effective(
    block: NetworkResilienceCritiqueBlock,
) -> bool:
    return _llm_effective_kind(block, _NETWORK)
