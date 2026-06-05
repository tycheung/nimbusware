from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class ResearchWorkflowBlock:
    enabled: bool = False
    domain_enabled: bool = True
    code_enabled: bool = True
    max_brief_sources: int = 20
    pattern_index_contribution: bool = True


_DEFAULT_LICENSE_ALLOWLIST = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause")


@dataclass(frozen=True)
class StitchWorkflowBlock:
    enabled: bool = False
    max_files: int = 40
    max_loc: int = 2500
    max_new_dependencies: int = 10
    license_allowlist: tuple[str, ...] = _DEFAULT_LICENSE_ALLOWLIST
    require_refactor_pass: bool = True


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    return default


def parse_research_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> ResearchWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("research")
    if not isinstance(raw, dict):
        return ResearchWorkflowBlock()
    return ResearchWorkflowBlock(
        enabled=_coerce_bool(raw.get("enabled"), default=False),
        domain_enabled=_coerce_bool(raw.get("domain_enabled"), default=True),
        code_enabled=_coerce_bool(raw.get("code_enabled"), default=True),
        max_brief_sources=max(1, min(50, int(raw.get("max_brief_sources", 20) or 20))),
        pattern_index_contribution=_coerce_bool(
            raw.get("pattern_index_contribution"),
            default=True,
        ),
    )


def parse_stitch_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> StitchWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("stitch")
    if not isinstance(raw, dict):
        return StitchWorkflowBlock()
    license_raw = raw.get("license_allowlist")
    licenses: tuple[str, ...] = _DEFAULT_LICENSE_ALLOWLIST
    if isinstance(license_raw, list):
        cleaned = [str(x).strip() for x in license_raw if str(x).strip()]
        if cleaned:
            licenses = tuple(cleaned)
    return StitchWorkflowBlock(
        enabled=_coerce_bool(raw.get("enabled"), default=False),
        max_files=max(1, int(raw.get("max_files", 40) or 40)),
        max_loc=max(1, int(raw.get("max_loc", 2500) or 2500)),
        max_new_dependencies=max(0, int(raw.get("max_new_dependencies", 10) or 10)),
        license_allowlist=licenses,
        require_refactor_pass=_coerce_bool(raw.get("require_refactor_pass"), default=True),
    )


def research_effective_metadata(block: ResearchWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "domain_enabled": block.domain_enabled,
        "code_enabled": block.code_enabled,
        "max_brief_sources": block.max_brief_sources,
        "pattern_index_contribution": block.pattern_index_contribution,
    }


def stitch_effective_metadata(block: StitchWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "max_files": block.max_files,
        "max_loc": block.max_loc,
        "max_new_dependencies": block.max_new_dependencies,
        "license_allowlist": list(block.license_allowlist),
        "require_refactor_pass": block.require_refactor_pass,
    }
