from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from nimbusware_orchestrator.security_semgrep import run_semgrep_scan, semgrep_enabled


def test_semgrep_disabled() -> None:
    with patch.dict(os.environ, {"NIMBUSWARE_RUN_SEMGREP": "0"}, clear=False):
        code, msg = run_semgrep_scan(Path("."))
    assert code == 0
    assert "skipped" in msg.lower()


@patch("nimbusware_orchestrator.security_semgrep.shutil.which", return_value=None)
def test_semgrep_missing_binary(_which: object) -> None:
    with patch.dict(os.environ, {"NIMBUSWARE_RUN_SEMGREP": "1"}, clear=False):
        code, msg = run_semgrep_scan(Path("."))
    assert code == 0
    assert "PATH" in msg


def test_semgrep_enabled_default() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NIMBUSWARE_RUN_SEMGREP", None)
    assert semgrep_enabled() is True
