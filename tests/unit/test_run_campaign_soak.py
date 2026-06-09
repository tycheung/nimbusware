from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_campaign_soak as campaign_soak_mod  # noqa: E402


def test_run_campaign_soak_skips_when_no_journeys(tmp_path: Path) -> None:
    summary = campaign_soak_mod.run_campaign_soak(repo_root=tmp_path)
    assert summary["skipped"] is True
    assert summary["passed"] is False


def test_run_campaign_soak_passes_when_pytest_succeeds(tmp_path: Path) -> None:
    journey_dir = tmp_path / "tests" / "e2e" / "journeys"
    journey_dir.mkdir(parents=True)
    journey = journey_dir / "test_fake_campaign_journey.py"
    journey.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    rel = "tests/e2e/journeys/test_fake_campaign_journey.py"
    with patch.dict(os.environ, {"NIMBUSWARE_CAMPAIGN_SOAK_JOURNEYS": rel}):
        with patch("run_campaign_soak.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            summary = campaign_soak_mod.run_campaign_soak(repo_root=tmp_path)
    assert summary["passed"] is True
    assert mock_run.call_count >= 1
