from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Literal

from env.env_flags import env_str, env_truthy
from orchestrator.llm.common import ollama_chat_json_via_plan_patch


def _run_test_writer_stage_subprocess(workspace: Path) -> tuple[int, str]:
    cmd_raw = env_str(
        "NIMBUSWARE_TEST_WRITER_STAGE_CMD",
        default="python -m pytest -q -k test_writer --maxfail=1",
    )
    cmd = shlex.split(cmd_raw) if cmd_raw else []
    if not cmd:
        return 0, "test_writer stage command omitted"
    proc = subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(x for x in (proc.stdout, proc.stderr) if x).strip()
    return int(proc.returncode), output


def _run_test_writer_stage_llm(
    *,
    model_id: str,
    base_url: str,
    timeout_seconds: float,
) -> tuple[int, str]:
    try:
        payload = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            timeout_seconds=timeout_seconds,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a test-writer assistant. Return JSON object with keys "
                        "status, summary, suggested_tests_count."
                    ),
                },
                {
                    "role": "user",
                    "content": "Suggest lightweight tests for the current workspace.",
                },
            ],
            agent_role="test_writer",
        )
    except Exception as exc:  # pragma: no cover - exercised via fallback tests
        return 1, f"llm test-writer failed: {str(exc)[:200]}"
    summary = str(payload.get("summary", "llm test-writer completed")).strip()
    return 0, summary[:500]


def run_test_writer_stage(
    workspace: Path,
    *,
    llm_body_enabled: bool = False,
    llm_stub_fallback: bool = False,
    llm_model_id: str | None = None,
    llm_base_url: str = "http://localhost:11434",
    llm_timeout_seconds: float = 120.0,
) -> tuple[int, str, Literal["subprocess", "llm", "stub"]]:
    """Run a configurable command for the test-writer stage.

    Defaults to a lightweight pytest invocation so this can be enabled without
    introducing a second full verifier bundle execution.
    """
    if llm_body_enabled and env_truthy("NIMBUSWARE_USE_LLM"):
        if env_truthy("NIMBUSWARE_TEST_WRITER_LLM_STUB"):
            return 0, "stub test-writer llm body", "stub"
        if llm_model_id:
            code, out = _run_test_writer_stage_llm(
                model_id=llm_model_id,
                base_url=llm_base_url,
                timeout_seconds=llm_timeout_seconds,
            )
            if code == 0:
                return code, out, "llm"
            if llm_stub_fallback:
                return 0, "stub fallback after llm failure", "stub"
            return code, out, "llm"
        if llm_stub_fallback:
            return 0, "stub fallback without selected model", "stub"
    code, output = _run_test_writer_stage_subprocess(workspace)
    return code, output, "subprocess"
