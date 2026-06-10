from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import env_tri_state, nimbusware_use_llm_explicitly_off
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


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
