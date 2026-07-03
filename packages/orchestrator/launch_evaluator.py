from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from env.env_flags import env_bool, env_str
from orchestrator.ollama_manage import ollama_base_url


@dataclass(frozen=True)
class LaunchEvalScorecard:
    aggregate: float
    maturity: float
    maintainability: float
    scalability: float
    security: float
    testability: float
    findings: tuple[str, ...]
    passed: bool
    llm_findings: tuple[str, ...] = field(default_factory=tuple)
    llm_dimensions: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    plain_summary: str = ""
    dev_env_live_regression_passed: bool | None = None
    dev_env_http_regression_passed: bool | None = None
    dev_env_ui_regression_passed: bool | None = None
    put_ui_flow_id: str | None = None
    slice_e2e_passed: bool | None = None
    dev_env_ui_failed_step: int | None = None
    dev_env_ui_failed_locator: str | None = None

    def to_dict(self) -> dict[str, object]:
        optional_keys = (
            "findings",
            "llm_findings",
            "llm_dimensions",
            "dev_env_live_regression_passed",
            "dev_env_http_regression_passed",
            "dev_env_ui_regression_passed",
            "put_ui_flow_id",
            "slice_e2e_passed",
            "dev_env_ui_failed_step",
            "dev_env_ui_failed_locator",
        )
        payload = {k: v for k, v in asdict(self).items() if k not in optional_keys}
        payload["findings"] = list(self.findings)
        if self.llm_findings:
            payload["llm_findings"] = list(self.llm_findings)
        if self.llm_dimensions:
            payload["llm_dimensions"] = {k: v for k, v in self.llm_dimensions}
        if self.dev_env_live_regression_passed is not None:
            payload["dev_env_live_regression_passed"] = self.dev_env_live_regression_passed
        if self.dev_env_http_regression_passed is not None:
            payload["dev_env_http_regression_passed"] = self.dev_env_http_regression_passed
        if self.dev_env_ui_regression_passed is not None:
            payload["dev_env_ui_regression_passed"] = self.dev_env_ui_regression_passed
        if self.put_ui_flow_id:
            payload["put_ui_flow_id"] = self.put_ui_flow_id
        if self.slice_e2e_passed is not None:
            payload["slice_e2e_passed"] = self.slice_e2e_passed
        if self.dev_env_ui_failed_step is not None:
            payload["dev_env_ui_failed_step"] = self.dev_env_ui_failed_step
        if self.dev_env_ui_failed_locator:
            payload["dev_env_ui_failed_locator"] = self.dev_env_ui_failed_locator
        if self.plain_summary:
            payload["plain_summary"] = self.plain_summary
        return payload


def llm_panel_enabled() -> bool:
    return env_bool("NIMBUSWARE_LAUNCH_EVAL_LLM")


def _launch_eval_llm_model() -> str:
    return env_str("NIMBUSWARE_LAUNCH_EVAL_LLM_MODEL") or "llama3.2"


def _workspace_llm_context(workspace: Path) -> str:
    ws = workspace.resolve()
    parts: list[str] = []
    readme = ws / "README.md"
    if readme.is_file():
        parts.append(readme.read_text(encoding="utf-8")[:1200])
    py_files = sorted(str(p.relative_to(ws)) for p in ws.rglob("*.py"))[:40]
    if py_files:
        parts.append("Python files: " + ", ".join(py_files))
    tests = sorted(str(p.relative_to(ws)) for p in ws.rglob("tests/test_*.py"))[:20]
    if tests:
        parts.append("Tests: " + ", ".join(tests))
    return "\n\n".join(parts) if parts else ws.name


_RUBRIC_DIMENSIONS = frozenset(
    {"maturity", "maintainability", "scalability", "security", "testability"},
)


def fetch_llm_rubric_panel(workspace: Path) -> dict[str, Any] | None:
    import httpx

    from orchestrator.llm.common import ollama_chat_json_via_plan_patch

    try:
        data = ollama_chat_json_via_plan_patch(
            base_url=ollama_base_url(),
            model=_launch_eval_llm_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Assess workspace launch readiness. Return JSON with "
                        '"findings": ["note", ...] (max 5 strings) and '
                        '"dimensions": {"maturity":0-10,"maintainability":0-10,'
                        '"scalability":0-10,"security":0-10,"testability":0-10}.'
                    ),
                },
                {"role": "user", "content": _workspace_llm_context(workspace)},
            ],
            timeout_seconds=30.0,
            agent_role="planner",
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError, httpx.HTTPError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _parse_llm_dimensions(raw: object) -> tuple[tuple[str, float], ...]:
    if not isinstance(raw, dict):
        return ()
    out: list[tuple[str, float]] = []
    for key, value in raw.items():
        if key not in _RUBRIC_DIMENSIONS:
            continue
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        out.append((key, _cap(score)))
    return tuple(out)


def _llm_panel_extras(workspace: Path) -> tuple[tuple[str, ...], tuple[tuple[str, float], ...]]:
    if not llm_panel_enabled():
        return (), ()
    panel = fetch_llm_rubric_panel(workspace)
    if panel:
        findings_raw = panel.get("findings")
        findings: tuple[str, ...] = ()
        if isinstance(findings_raw, list):
            findings = tuple(str(item).strip()[:400] for item in findings_raw if str(item).strip())[
                :5
            ]
        dimensions = _parse_llm_dimensions(panel.get("dimensions"))
        if findings or dimensions:
            return findings, dimensions
    py_count = len(list(workspace.rglob("*.py")))
    test_count = len(list(workspace.rglob("tests/test_*.py")))
    return (
        (
            f"advisory: {py_count} python modules and {test_count} test modules — "
            "confirm product intent manually (LLM unavailable)",
        ),
        (),
    )


def _cap(value: float) -> float:
    return min(10.0, value)


def _plain_launch_summary(
    aggregate: float,
    passed: bool,
    findings: tuple[str, ...],
) -> str:
    status = "ready to launch" if passed else "needs work before launch"
    base = f"Overall {aggregate:.1f}/10 — {status}"
    if findings:
        return f"{base}. Top note: {findings[0]}"
    return base


def _score_has_file(workspace: Path, pattern: str, *, points: float) -> tuple[float, str | None]:
    if list(workspace.rglob(pattern)):
        return points, None
    return 0.0, f"missing {pattern}"


def evaluate_workspace_rubric(
    workspace: Path,
    *,
    min_aggregate: float = 5.0,
) -> LaunchEvalScorecard:
    ws = workspace.resolve()
    findings: list[str] = []
    maturity = 0.0
    maintainability = 0.0
    scalability = 0.0
    security = 0.0
    testability = 0.0

    for pattern, pts, bucket in (
        ("README.md", 2.0, "maturity"),
        ("pyproject.toml", 2.0, "maintainability"),
        ("requirements.txt", 1.0, "maintainability"),
        ("tests/test_*.py", 3.0, "testability"),
        ("src/**/*.py", 2.0, "maintainability"),
        ("**/*.html", 1.0, "scalability"),
    ):
        pts_awarded, finding = _score_has_file(ws, pattern, points=pts)
        if finding:
            findings.append(finding)
        if bucket == "maturity":
            maturity += pts_awarded
        elif bucket == "maintainability":
            maintainability += pts_awarded
        elif bucket == "testability":
            testability += pts_awarded
        elif bucket == "scalability":
            scalability += pts_awarded

    if (ws / ".env").is_file():
        findings.append("workspace contains .env — rotate secrets")
        security = 2.0
    else:
        security = 5.0

    if list(ws.rglob("tests/test_*.py")):
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
            cwd=ws,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            testability += 4.0
        else:
            findings.append("pytest collect failed")
    else:
        testability += 2.0

    maturity = _cap(maturity)
    maintainability = _cap(maintainability)
    scalability = _cap(scalability)
    security = _cap(security)
    testability = _cap(testability)
    dims = (maturity, maintainability, scalability, security, testability)
    aggregate = round(sum(dims) / len(dims), 2)
    passed = aggregate >= min_aggregate and not any(
        f.startswith("pytest collect failed") for f in findings
    )
    llm_findings, llm_dimensions = _llm_panel_extras(ws)
    plain = _plain_launch_summary(aggregate, passed, tuple(findings))
    return LaunchEvalScorecard(
        aggregate=aggregate,
        maturity=maturity,
        maintainability=maintainability,
        scalability=scalability,
        security=security,
        testability=testability,
        findings=tuple(findings),
        passed=passed,
        llm_findings=llm_findings,
        llm_dimensions=llm_dimensions,
        plain_summary=plain,
    )


def merge_dev_env_into_scorecard(
    scorecard: LaunchEvalScorecard,
    rows: list[dict[str, Any]],
) -> LaunchEvalScorecard:
    from orchestrator.dev_env_launch_merge import dev_env_live_regression_from_rows

    bits = dev_env_live_regression_from_rows(rows)
    if not bits:
        return scorecard
    http = bits.get("dev_env_http_regression_passed")
    ui = bits.get("dev_env_ui_regression_passed")
    live = bits.get("dev_env_live_regression_passed")
    findings = list(scorecard.findings)
    if http is False:
        findings.append("dev_env HTTP regression failed")
    if ui is False:
        findings.append("dev_env UI regression failed")
    passed = scorecard.passed
    if live is False:
        passed = False
    flow_id = bits.get("put_ui_flow_id")
    slice_e2e = bits.get("slice_e2e_passed")
    failed_step = bits.get("dev_env_ui_failed_step")
    failed_locator = bits.get("dev_env_ui_failed_locator")
    return LaunchEvalScorecard(
        aggregate=scorecard.aggregate,
        maturity=scorecard.maturity,
        maintainability=scorecard.maintainability,
        scalability=scorecard.scalability,
        security=scorecard.security,
        testability=scorecard.testability,
        findings=tuple(findings),
        passed=passed,
        llm_findings=scorecard.llm_findings,
        llm_dimensions=scorecard.llm_dimensions,
        dev_env_live_regression_passed=(bool(live) if isinstance(live, bool) else None),
        dev_env_http_regression_passed=http if isinstance(http, bool) else None,
        dev_env_ui_regression_passed=ui if isinstance(ui, bool) else None,
        put_ui_flow_id=str(flow_id) if flow_id else None,
        slice_e2e_passed=slice_e2e if isinstance(slice_e2e, bool) else None,
        dev_env_ui_failed_step=int(failed_step) if failed_step is not None else None,
        dev_env_ui_failed_locator=str(failed_locator) if failed_locator else None,
        plain_summary=scorecard.plain_summary,
    )


def emit_launch_eval_completed(
    store: Any,
    run_id: UUID,
    scorecard: LaunchEvalScorecard,
    *,
    attach_context: dict[str, str] | None = None,
) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import (
        EventType,
        StagePassedEvent,
        StagePassedPayload,
        StageStartedEvent,
        StageStartedPayload,
    )

    meta = {**scorecard.to_dict(), "maker_approval": True}
    if attach_context:
        meta["attach_context"] = attach_context
    now = datetime.now(timezone.utc)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="launch_eval.completed", attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StagePassedPayload(stage_name="launch_eval.completed", duration_ms=0),
        ),
    )


def maybe_run_launch_eval_for_campaign(
    store: Any,
    run_id: UUID,
    rows: list[dict[str, Any]],
    *,
    workspace: Path | None = None,
) -> LaunchEvalScorecard | None:
    from maker.workspace import resolve_run_workspace

    if any(
        row.get("event_type") == "stage.passed"
        and isinstance(row.get("payload"), dict)
        and row["payload"].get("stage_name") == "launch_eval.completed"
        for row in rows
    ):
        return None
    ws = workspace or resolve_run_workspace(rows)
    if not ws.is_dir():
        return None
    from orchestrator.launch_eval_catalog import attach_context_from_run

    scorecard = evaluate_workspace_rubric(ws)
    scorecard = merge_dev_env_into_scorecard(scorecard, rows)
    emit_launch_eval_completed(
        store,
        run_id,
        scorecard,
        attach_context=attach_context_from_run(rows),
    )
    return scorecard
