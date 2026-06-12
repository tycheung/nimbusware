from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _run(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_REPO / "scripts" / script)],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_intent_to_patch_ci_gate_passes() -> None:
    proc = _run("run_intent_to_patch_ci_gate.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_classifier_acceptance_ci_gate_passes() -> None:
    proc = _run("run_classifier_acceptance_ci_gate.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_classifier_snapshot_meets_target_field() -> None:
    snap = _REPO / "benchmarks" / "latest_classifier_acceptance.json"
    body = json.loads(snap.read_text(encoding="utf-8"))
    assert body.get("meets_target") is True
    assert float(body["rate"]) >= float(body.get("target_rate", 0.7))
