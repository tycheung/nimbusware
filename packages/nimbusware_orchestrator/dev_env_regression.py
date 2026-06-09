from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.dev_env_events import emit_dev_env_regression
from nimbusware_orchestrator.dev_env_supervisor import active_base_url
from nimbusware_orchestrator.put_e2e_runner import (
    PutE2EResult,
    match_factory_flow_id,
    run_put_e2e_flow,
)


@dataclass(frozen=True)
class DevEnvRegressionResult:
    passed: bool
    baseline_captured: bool = False
    detail: str = ""
    put_e2e: PutE2EResult | None = None
    diff: dict[str, Any] = field(default_factory=dict)


def _baseline_path(workspace: Path) -> Path:
    return workspace.resolve() / ".nimbusware" / "dev_env" / "regression_baseline.json"


def capture_regression_baseline(
    workspace: Path,
    *,
    flow_id: str,
    put_e2e: PutE2EResult,
) -> Path:
    path = _baseline_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "flow_id": flow_id,
        "verdict": put_e2e.verdict,
        "findings_count": len(put_e2e.findings),
        "exercised_paths": sorted(put_e2e.exercised_paths),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_regression_baseline(workspace: Path) -> dict[str, Any] | None:
    path = _baseline_path(workspace)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def run_dev_env_regression(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    prompt: str = "",
    prompt_id: str | None = None,
    flow_id: str | None = None,
    emit_events: bool = True,
    capture_baseline_if_missing: bool = True,
) -> DevEnvRegressionResult:
    ws = workspace.resolve()
    base_url = active_base_url(ws)
    if not base_url:
        result = DevEnvRegressionResult(passed=False, detail="dev_env_not_running")
        if emit_events:
            emit_dev_env_regression(store, run_id, passed=False, detail=result.detail)
        return result

    resolved_flow = flow_id or match_factory_flow_id(prompt, prompt_id=prompt_id)
    put_result = run_put_e2e_flow(resolved_flow, base_url=base_url, workspace=ws)
    passed = put_result.verdict == "PASS"
    baseline = load_regression_baseline(ws)
    diff: dict[str, Any] = {}
    baseline_captured = False

    if baseline is None and passed and capture_baseline_if_missing:
        capture_regression_baseline(ws, flow_id=resolved_flow, put_e2e=put_result)
        baseline_captured = True
    elif baseline is not None:
        diff = {
            "baseline_verdict": baseline.get("verdict"),
            "current_verdict": put_result.verdict,
            "regressed": baseline.get("verdict") == "PASS" and not passed,
        }

    detail = "pass" if passed else f"put_e2e_{put_result.verdict.lower()}"
    if diff.get("regressed"):
        detail = "regression_detected"

    outcome = DevEnvRegressionResult(
        passed=passed and not diff.get("regressed"),
        baseline_captured=baseline_captured,
        detail=detail,
        put_e2e=put_result,
        diff=diff,
    )
    if emit_events:
        emit_dev_env_regression(
            store,
            run_id,
            passed=outcome.passed,
            detail=outcome.detail,
            metadata={"flow_id": resolved_flow, "diff": diff},
        )
    return outcome
