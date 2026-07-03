from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.materializer import ConfigMaterializer
from env.settings_resolve import resolve_explicit_raw
from orchestrator.workflow.profiles import (
    collect_workflow_extends_trace,
    workflow_profile_dict,
)


@dataclass(frozen=True)
class ResolvedConfig:
    repo_root: Path
    workflow_profile: str
    workflow_dict: dict[str, Any]
    materializer_generation: int
    materializer_use_db: bool
    trace: tuple[str, ...]
    materializer: ConfigMaterializer | None = None


def _resolve_workflow_profile_name(workflow_profile: str | None, trace: list[str]) -> str:
    if workflow_profile is not None and str(workflow_profile).strip():
        name = str(workflow_profile).strip()
        trace.append(f"arg:workflow_profile={name}")
        return name
    default_raw = resolve_explicit_raw("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE")
    if default_raw:
        trace.append(f"env:NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE={default_raw}")
        return default_raw
    legacy_raw = os.environ.get("NIMBUSWARE_WORKFLOW_PROFILE", "").strip()
    if legacy_raw:
        trace.append(f"env:NIMBUSWARE_WORKFLOW_PROFILE={legacy_raw} (legacy)")
        return legacy_raw
    trace.append("default:workflow_profile=micro_slice")
    return "micro_slice"


def resolve_run_config(
    repo_root: Path,
    workflow_profile: str | None = None,
    *,
    materializer: ConfigMaterializer | None = None,
) -> ResolvedConfig:
    root = repo_root.resolve()
    trace: list[str] = []
    profile = _resolve_workflow_profile_name(workflow_profile, trace)
    mat = materializer or ConfigMaterializer(root)
    trace.append(f"materializer:use_db={mat.use_db} generation={mat.generation}")
    trace.extend(collect_workflow_extends_trace(root, profile, materializer=mat))
    merged = workflow_profile_dict(root, profile, materializer=mat)
    trace.append(f"yaml:resolved profile={profile}")
    return ResolvedConfig(
        repo_root=root,
        workflow_profile=profile,
        workflow_dict=merged,
        materializer_generation=mat.generation,
        materializer_use_db=mat.use_db,
        trace=tuple(trace),
        materializer=mat,
    )


def effective_universal_critique_from_resolved(resolved: ResolvedConfig) -> Any:
    from orchestrator.workflow.universal_critique import effective_universal_critique

    return effective_universal_critique(
        resolved.repo_root,
        resolved.workflow_profile,
        config_materializer=resolved.materializer,
        resolved_config=resolved,
    )
