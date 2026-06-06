"""Deterministic workspace quality rubric (launch eval v0)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID


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

    def to_dict(self) -> dict[str, object]:
        payload = {k: v for k, v in asdict(self).items() if k not in ("findings", "llm_findings")}
        payload["findings"] = list(self.findings)
        if self.llm_findings:
            payload["llm_findings"] = list(self.llm_findings)
        return payload


def llm_panel_enabled() -> bool:
    raw = os.environ.get("NIMBUSWARE_LAUNCH_EVAL_LLM", "").strip().lower()
    return raw in ("1", "true", "yes")


def _launch_eval_llm_model() -> str:
    explicit = os.environ.get("NIMBUSWARE_LAUNCH_EVAL_LLM_MODEL", "").strip()
    if explicit:
        return explicit
    fallback = os.environ.get("NIMBUSWARE_OLLAMA_DEFAULT_MODEL", "").strip()
    return fallback or "llama3.2"


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").strip()


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


def fetch_llm_rubric_findings(workspace: Path) -> tuple[str, ...] | None:
    import httpx

    from nimbusware_orchestrator.ollama_chat import ollama_chat_json

    try:
        data = ollama_chat_json(
            base_url=_ollama_base_url(),
            model=_launch_eval_llm_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Assess workspace launch readiness. Return JSON "
                        '{"findings": ["note1", ...]} with up to 5 concise strings.'
                    ),
                },
                {"role": "user", "content": _workspace_llm_context(workspace)},
            ],
            timeout_seconds=30.0,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError, httpx.HTTPError):
        return None
    raw = data.get("findings")
    if not isinstance(raw, list):
        return None
    out = tuple(str(item).strip()[:400] for item in raw if str(item).strip())[:5]
    return out or None


def _llm_advisory_findings(workspace: Path) -> tuple[str, ...]:
    if not llm_panel_enabled():
        return ()
    llm = fetch_llm_rubric_findings(workspace)
    if llm:
        return llm
    py_count = len(list(workspace.rglob("*.py")))
    test_count = len(list(workspace.rglob("tests/test_*.py")))
    return (
        f"advisory: {py_count} python modules and {test_count} test modules — "
        "confirm product intent manually (LLM unavailable)",
    )


def _cap(value: float) -> float:
    return min(10.0, value)


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
    llm_findings = _llm_advisory_findings(ws)
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
    )


def emit_launch_eval_completed(store: Any, run_id: UUID, scorecard: LaunchEvalScorecard) -> None:
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
    from nimbusware_maker.workspace import resolve_run_workspace

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
    scorecard = evaluate_workspace_rubric(ws)
    emit_launch_eval_completed(store, run_id, scorecard)
    return scorecard
