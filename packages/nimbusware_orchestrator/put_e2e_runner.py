from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_orchestrator.put_e2e_capture import (
    _playwright_module_ready,
    http_flow_stub_findings,
    stub_capture_sections,
    stub_console_capture,
    stub_network_capture,
)
from nimbusware_orchestrator.put_e2e_factory_flows import (
    factory_flows_root,
    list_factory_flow_ids,
    load_factory_flow,
    load_factory_flow_catalog,
    match_factory_flow_id,
)
from nimbusware_orchestrator.put_e2e_http_steps import _run_http_step
from nimbusware_orchestrator.put_e2e_types import PutE2EFinding, PutE2EResult, PutE2EVerdict

__all__ = [
    "PutE2EFinding",
    "PutE2EResult",
    "PutE2EVerdict",
    "_playwright_module_ready",
    "factory_flows_root",
    "list_factory_flow_ids",
    "load_factory_flow",
    "load_factory_flow_catalog",
    "match_factory_flow_id",
    "run_put_e2e_flow",
    "http_flow_stub_findings",
    "stub_capture_sections",
    "stub_console_capture",
    "stub_network_capture",
]


def run_put_e2e_flow(
    base_url: str,
    flow_id: str,
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
    timeout_seconds: float = 60.0,
    require_playwright: bool = False,
) -> PutE2EResult:
    try:
        flow = load_factory_flow(flow_id, repo_root=repo_root)
    except (KeyError, OSError, yaml.YAMLError) as exc:
        return PutE2EResult(
            verdict="FAIL",
            flow_id=flow_id,
            base_url=base_url,
            detail=str(exc),
        )

    pw_ready, pw_detail = _playwright_module_ready()
    if require_playwright and not pw_ready:
        return PutE2EResult(
            verdict="SKIP",
            flow_id=flow_id,
            base_url=base_url,
            detail=pw_detail,
        )

    capture_cfg = mapping_or_empty(flow.get("capture"))
    console_on = bool(capture_cfg.get("console", False))
    network_on = bool(capture_cfg.get("network", False))

    exercised: set[str] = set()
    findings: list[PutE2EFinding] = []
    steps_raw = flow.get("steps")
    steps: list[Any] = steps_raw if isinstance(steps_raw, list) else []

    def _failed_goto_path() -> str:
        for finding in reversed(findings):
            if finding.surface_path:
                return finding.surface_path
        for step in reversed(steps):
            if isinstance(step, dict) and str(step.get("action") or "").strip().lower() == "goto":
                return str(step.get("path") or "/")
        return next(iter(exercised), "/")

    def _success_goto_path() -> str:
        for step in steps:
            if isinstance(step, dict) and str(step.get("action") or "").strip().lower() == "goto":
                return str(step.get("path") or "/")
        return next(iter(exercised), "/")

    def _attach_browser_capture(
        capture: dict[str, Any],
        *,
        goto_path: str,
        exercised_paths: set[str],
    ) -> dict[str, Any]:
        if workspace is None or not workspace.is_dir():
            return capture
        if not (console_on or network_on or require_playwright or pw_ready):
            return capture
        from nimbusware_orchestrator.put_e2e_browser import capture_failure_browser_trace
        from nimbusware_orchestrator.put_e2e_evidence import put_e2e_evidence_dir

        evidence_dir = put_e2e_evidence_dir(workspace, flow_id)
        trace_meta = capture_failure_browser_trace(
            base_url,
            goto_path,
            evidence_dir=evidence_dir,
            capture_console=console_on,
            capture_network=network_on,
        )
        if not trace_meta:
            return capture
        out = dict(capture)
        out["trace"] = trace_meta
        live_findings = trace_meta.get("findings") or []
        if live_findings:
            out["console"] = [row for row in live_findings if row.get("kind") == "console"]
            out["network"] = [row for row in live_findings if row.get("kind") == "network"]
        elif console_on or network_on:
            sections = stub_capture_sections(
                console_on=console_on,
                network_on=network_on,
                exercised_paths=exercised_paths,
            )
            out["console"] = sections["console"]
            out["network"] = sections["network"]
        return out

    def _fail_result(
        *,
        detail: str,
        exercised_paths: set[str],
        capture: dict[str, Any],
    ) -> PutE2EResult:
        if workspace is not None and workspace.is_dir():
            from nimbusware_orchestrator.put_e2e_evidence import write_put_e2e_failure_evidence

            capture = _attach_browser_capture(
                capture,
                goto_path=_failed_goto_path(),
                exercised_paths=exercised_paths,
            )
            pending = PutE2EResult(
                verdict="FAIL",
                flow_id=flow_id,
                base_url=base_url,
                detail=detail,
                exercised_paths=exercised_paths,
                findings=findings,
                capture=capture,
            )
            evidence = write_put_e2e_failure_evidence(workspace, pending)
            capture = dict(capture)
            capture["evidence"] = evidence
            pending.capture = capture
            return pending
        return PutE2EResult(
            verdict="FAIL",
            flow_id=flow_id,
            base_url=base_url,
            detail=detail,
            exercised_paths=exercised_paths,
            findings=findings,
            capture=capture,
        )

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if not _run_http_step(
                    client, base_url, step, exercised=exercised, findings=findings
                ):
                    step_capture = stub_capture_sections(
                        console_on=console_on,
                        network_on=network_on,
                        exercised_paths=exercised,
                    )
                    detail = findings[-1].message if findings else "flow step failed"
                    return _fail_result(
                        detail=detail,
                        exercised_paths=exercised,
                        capture=step_capture,
                    )
    except httpx.HTTPError as exc:
        return _fail_result(
            detail=str(exc),
            exercised_paths=exercised,
            capture={},
        )

    findings.extend(
        http_flow_stub_findings(
            console_on=console_on,
            network_on=network_on,
            exercised_paths=exercised,
        ),
    )
    capture: dict[str, Any] = {
        "console": [f.to_dict() for f in findings if f.kind == "console"],
        "network": [f.to_dict() for f in findings if f.kind == "network"],
        "playwright_ready": pw_ready,
        "playwright_detail": pw_detail,
    }
    capture = _attach_browser_capture(
        capture,
        goto_path=_success_goto_path(),
        exercised_paths=exercised,
    )
    from nimbusware_orchestrator.fleet_playwright import (
        attach_fleet_playwright_capture,
        fleet_browser_goto,
        fleet_playwright_config,
    )

    capture = attach_fleet_playwright_capture(capture)
    fleet_cfg = fleet_playwright_config()
    if fleet_cfg.get("enabled") and steps:
        first = steps[0] if isinstance(steps[0], dict) else {}
        goto_path = (
            str(first.get("path") or "/") if str(first.get("action") or "") == "goto" else "/"
        )
        capture["fleet_browser"] = fleet_browser_goto(base_url, goto_path)
    return PutE2EResult(
        verdict="PASS",
        flow_id=flow_id,
        base_url=base_url,
        detail="all flow steps passed",
        exercised_paths=exercised,
        findings=findings,
        capture=capture,
    )
