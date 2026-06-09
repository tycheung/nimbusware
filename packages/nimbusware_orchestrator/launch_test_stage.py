"""Launch-test writer/critic stage executor."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.js_framework_detect import detect_js_framework, load_framework_pack
from nimbusware_orchestrator.ui_flow_synthesis import (
    synthesize_ui_flow_from_ism,
    validate_ui_flow_yaml,
    write_draft_ui_flow,
)


@dataclass
class LaunchTestStageResult:
    passed: bool
    detail: str = ""
    flow_id: str = ""
    pack_id: str = ""
    critique_verdict: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)


def _load_prompt(name: str) -> str:
    path = find_repo_root() / "configs" / "prompts" / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def build_launch_test_writer_prompt(workspace: Path, *, repo_root: Path | None = None) -> str:
    root = repo_root or find_repo_root()
    base = _load_prompt("launch_test_writer_stable.txt")
    pack_id = detect_js_framework(workspace, repo_root=root)
    pack = load_framework_pack(pack_id, repo_root=root)
    instructions = str(pack.get("writer_instructions") or "").strip()
    if not instructions:
        return base
    return f"{base}\n\n## Framework pack ({pack_id})\n{instructions}"


def _critique_flow(flow_yaml: dict[str, Any]) -> tuple[bool, str, list[str]]:
    errors = validate_ui_flow_yaml(flow_yaml)
    for step in flow_yaml.get("steps") or []:
        if not isinstance(step, dict):
            continue
        loc = step.get("locator") or {}
        if isinstance(loc, dict) and loc.get("strategy") == "css":
            val = str(loc.get("value") or "")
            if "nth-child" in val:
                errors.append("positional_css_locator")
    if errors:
        return False, "FAIL", errors
    return True, "PASS", []


def run_launch_test_plan(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
) -> LaunchTestStageResult:
    pack_id = detect_js_framework(workspace)
    pack = load_framework_pack(pack_id)
    flow = synthesize_ui_flow_from_ism(workspace, preview_base_url=preview_base_url)
    writer_prompt = build_launch_test_writer_prompt(workspace)
    return LaunchTestStageResult(
        passed=True,
        detail="plan_ready",
        flow_id=flow.flow_id,
        pack_id=pack_id,
        findings=[
            {"pack_version": pack.get("pack_version"), "surfaces": len(flow.steps)},
            {"writer_prompt": writer_prompt},
        ],
    )


def run_launch_test_write(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
    flow_id: str = "launch_draft",
) -> LaunchTestStageResult:
    flow = synthesize_ui_flow_from_ism(
        workspace, flow_id=flow_id, preview_base_url=preview_base_url
    )
    path = write_draft_ui_flow(workspace, flow)
    pack_id = detect_js_framework(workspace)
    return LaunchTestStageResult(
        passed=True,
        detail=f"wrote:{path.name}",
        flow_id=flow.flow_id,
        pack_id=pack_id,
        findings=[{"writer_prompt": build_launch_test_writer_prompt(workspace)}],
    )


def run_launch_test_critique(
    workspace: Path, *, flow_id: str = "launch_draft"
) -> LaunchTestStageResult:
    path = workspace / ".nimbusware" / "dev_env" / "ui_flows" / f"{flow_id}.yaml"
    if not path.is_file():
        return LaunchTestStageResult(passed=False, detail="missing_flow", flow_id=flow_id)
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ok, verdict, errors = _critique_flow(raw)
    return LaunchTestStageResult(
        passed=ok,
        detail=verdict,
        flow_id=flow_id,
        critique_verdict=verdict,
        findings=[{"error": e} for e in errors],
    )


def run_launch_test_stage(
    workspace: Path,
    stage_name: str,
    *,
    preview_base_url: str | None = None,
) -> tuple[int, str, Literal["plan", "write", "critique", "unknown"]]:
    if stage_name == "launch_test.plan":
        result = run_launch_test_plan(workspace, preview_base_url=preview_base_url)
        return (0 if result.passed else 1), result.detail, "plan"
    if stage_name == "launch_test.write":
        result = run_launch_test_write(workspace, preview_base_url=preview_base_url)
        return (0 if result.passed else 1), result.detail, "write"
    if stage_name == "launch_test.critique":
        result = run_launch_test_critique(workspace)
        return (0 if result.passed else 1), result.detail, "critique"
    if os.environ.get("NIMBUSWARE_LAUNCH_TEST_STUB", "").strip().lower() in ("1", "true", "yes"):
        return 0, "launch_test_stub", "unknown"
    return 1, f"unknown_launch_test_stage:{stage_name}", "unknown"
