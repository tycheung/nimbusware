"""Windows subprocess adapter smoke ."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only subprocess smoke")


def test_run_subprocess_cmd_echo() -> None:
    from nimbusware_executor.windows import run_subprocess

    proc = run_subprocess(
        ["cmd", "/c", "echo", "nimbusware-smoke"],
        cwd=Path(__file__).resolve().parent,
        timeout_seconds=15.0,
    )
    assert proc.returncode == 0
    assert "nimbusware-smoke" in (proc.stdout or "")
