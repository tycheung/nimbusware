from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orchestrator.test_writer_stage import run_test_writer_stage


def test_run_test_writer_stage_passes_exit_code_and_output() -> None:
    proc = SimpleNamespace(returncode=0, stdout="ok", stderr="")
    with patch("subprocess.run", return_value=proc):
        code, log, mode = run_test_writer_stage(Path("."))
    assert code == 0
    assert "ok" in log
    assert mode == "subprocess"


def test_run_test_writer_stage_uses_configured_command() -> None:
    proc = SimpleNamespace(returncode=2, stdout="", stderr="bad")
    with patch.dict(os.environ, {"NIMBUSWARE_TEST_WRITER_STAGE_CMD": "python -m pytest -q"}):
        with patch("subprocess.run", return_value=proc) as mock_run:
            code, log, mode = run_test_writer_stage(Path("."))
    assert code == 2
    assert "bad" in log
    assert mode == "subprocess"
    args = mock_run.call_args[0][0]
    assert args[:3] == ["python", "-m", "pytest"]
