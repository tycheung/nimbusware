from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_tools.risk_caps import AgentRiskCaps
from orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class PatchAutoApplyPolicy:
    max_loc: int = 40
    max_files: int = 1
    require_tests_passed: bool = True
    max_gate_severity: str = "MEDIUM"


@dataclass(frozen=True)
class PatchWorkflowBlock:
    enabled: bool = False
    targeted_test: bool = True
    skip_run_plan: bool = True
    auto_apply: PatchAutoApplyPolicy = PatchAutoApplyPolicy()
    risk_caps: AgentRiskCaps | None = None


def _parse_auto_apply(raw: Any) -> PatchAutoApplyPolicy:
    if not isinstance(raw, dict):
        return PatchAutoApplyPolicy()
    return PatchAutoApplyPolicy(
        max_loc=int(raw.get("max_loc", 40)),
        max_files=int(raw.get("max_files", 1)),
        require_tests_passed=bool(raw.get("require_tests_passed", True)),
        max_gate_severity=str(raw.get("max_gate_severity", "MEDIUM")).strip().upper() or "MEDIUM",
    )


def _parse_risk_caps(raw: Any) -> AgentRiskCaps | None:
    if not isinstance(raw, dict):
        return None
    try:
        return AgentRiskCaps(
            max_tool_steps=int(raw.get("max_tool_steps", 12)),
            max_shell_invocations=int(raw.get("max_shell_invocations", 3)),
            max_write_bytes=int(raw.get("max_write_bytes", 65536)),
        )
    except (TypeError, ValueError):
        return None


def parse_patch_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> PatchWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return PatchWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return PatchWorkflowBlock()
    patch_raw = raw.get("patch")
    if not isinstance(patch_raw, dict):
        if key == "patch":
            return PatchWorkflowBlock(enabled=True)
        return PatchWorkflowBlock()
    return PatchWorkflowBlock(
        enabled=True,
        targeted_test=bool(patch_raw.get("targeted_test", True)),
        skip_run_plan=bool(patch_raw.get("skip_run_plan", True)),
        auto_apply=_parse_auto_apply(patch_raw.get("auto_apply_policy")),
        risk_caps=_parse_risk_caps(patch_raw.get("risk_caps")),
    )


def patch_effective_metadata(block: PatchWorkflowBlock) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "enabled": block.enabled,
        "targeted_test": block.targeted_test,
        "skip_run_plan": block.skip_run_plan,
        "auto_apply_policy": {
            "max_loc": block.auto_apply.max_loc,
            "max_files": block.auto_apply.max_files,
            "require_tests_passed": block.auto_apply.require_tests_passed,
            "max_gate_severity": block.auto_apply.max_gate_severity,
        },
    }
    if block.risk_caps is not None:
        meta["risk_caps"] = block.risk_caps.to_metadata()
    return meta
