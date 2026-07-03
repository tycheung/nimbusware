from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from env import find_repo_root
from env.env_flags import env_truthy
from orchestrator.js_framework_detect import detect_js_framework, load_framework_pack
from orchestrator.ui_flow_synthesis import (
    synthesize_ui_flow_from_ism,
    validate_ui_flow_yaml,
    write_draft_ui_flow,
)

MAX_LAUNCH_TEST_WRITE_ATTEMPTS = 3


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


def _launch_pack_id(
    workspace: Path,
    *,
    requirements: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> str:
    from maker.stack_manifest import manifest_from_requirements
    from orchestrator.stack_catalog import stack_for_surface

    manifest = manifest_from_requirements(requirements)
    if manifest is not None:
        web_stack = stack_for_surface(manifest.model_dump(), "web", repo_root=repo_root)
        if web_stack is not None and web_stack.launch_framework_id:
            return web_stack.launch_framework_id
    return detect_js_framework(workspace, repo_root=repo_root)


def run_launch_test_plan(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
    requirements: dict[str, Any] | None = None,
) -> LaunchTestStageResult:
    pack_id = _launch_pack_id(workspace, requirements=requirements)
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


def _write_ui_flow_yaml(workspace: Path, raw: dict[str, Any], *, flow_id: str) -> Path:
    out_dir = workspace.resolve() / ".nimbusware" / "dev_env" / "ui_flows"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{flow_id}.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _write_flow_attempt(
    workspace: Path,
    *,
    preview_base_url: str | None,
    flow_id: str,
    attempt: int,
    critique_errors: tuple[str, ...],
) -> tuple[Path, str]:
    from orchestrator.launch_test_llm import (
        generate_llm_ui_flow_dict,
        launch_test_llm_enabled,
    )

    mode = "ism"
    if launch_test_llm_enabled():
        llm_raw = generate_llm_ui_flow_dict(
            workspace,
            flow_id=flow_id,
            preview_base_url=preview_base_url,
            critique_errors=critique_errors,
        )
        if llm_raw is not None:
            mode = "llm"
            path = _write_ui_flow_yaml(workspace, llm_raw, flow_id=flow_id)
            return path, mode
    flow = synthesize_ui_flow_from_ism(
        workspace, flow_id=flow_id, preview_base_url=preview_base_url
    )
    path = write_draft_ui_flow(workspace, flow)
    return path, mode


def run_launch_test_write(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
    flow_id: str = "launch_draft",
    requirements: dict[str, Any] | None = None,
) -> LaunchTestStageResult:
    pack_id = _launch_pack_id(workspace, requirements=requirements)
    findings: list[dict[str, Any]] = [
        {"writer_prompt": build_launch_test_writer_prompt(workspace)},
    ]
    critique_errors: tuple[str, ...] = ()
    last_detail = ""
    for attempt in range(1, MAX_LAUNCH_TEST_WRITE_ATTEMPTS + 1):
        path, mode = _write_flow_attempt(
            workspace,
            preview_base_url=preview_base_url,
            flow_id=flow_id,
            attempt=attempt,
            critique_errors=critique_errors,
        )
        critique = run_launch_test_critique(workspace, flow_id=flow_id)
        findings.append(
            {
                "attempt": attempt,
                "mode": mode,
                "critique": critique.critique_verdict,
                "errors": [f.get("error") for f in critique.findings if f.get("error")],
            },
        )
        if critique.passed:
            return LaunchTestStageResult(
                passed=True,
                detail=f"wrote:{path.name}:attempt={attempt}:mode={mode}",
                flow_id=flow_id,
                pack_id=pack_id,
                findings=findings,
            )
        critique_errors = tuple(
            str(f.get("error") or "") for f in critique.findings if f.get("error")
        )
        last_detail = critique.detail
    return LaunchTestStageResult(
        passed=False,
        detail=f"replan_exhausted:{last_detail}",
        flow_id=flow_id,
        pack_id=pack_id,
        critique_verdict="FAIL",
        findings=findings,
    )


def run_launch_test_critique(
    workspace: Path, *, flow_id: str = "launch_draft"
) -> LaunchTestStageResult:
    path = workspace / ".nimbusware" / "dev_env" / "ui_flows" / f"{flow_id}.yaml"
    if not path.is_file():
        return LaunchTestStageResult(passed=False, detail="missing_flow", flow_id=flow_id)
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
    requirements: dict[str, Any] | None = None,
) -> tuple[int, str, Literal["plan", "write", "critique", "unknown"]]:
    if stage_name == "launch_test.plan":
        result = run_launch_test_plan(
            workspace,
            preview_base_url=preview_base_url,
            requirements=requirements,
        )
        return (0 if result.passed else 1), result.detail, "plan"
    if stage_name == "launch_test.write":
        result = run_launch_test_write(
            workspace,
            preview_base_url=preview_base_url,
            requirements=requirements,
        )
        return (0 if result.passed else 1), result.detail, "write"
    if stage_name == "launch_test.critique":
        result = run_launch_test_critique(workspace)
        return (0 if result.passed else 1), result.detail, "critique"
    if env_truthy("NIMBUSWARE_LAUNCH_TEST_STUB"):
        return 0, "launch_test_stub", "unknown"
    return 1, f"unknown_launch_test_stage:{stage_name}", "unknown"
