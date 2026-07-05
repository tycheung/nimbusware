from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_AGG = _REPO / "scripts" / "ci" / "aggregate_stream_results.py"


def test_aggregate_stream_results_pass_and_fail(tmp_path: Path) -> None:
    ok = tmp_path / "hygiene.json"
    ok.write_text(json.dumps({"stream_id": "hygiene", "passed": True, "checks": []}), encoding="utf-8")
    fail = tmp_path / "lint.json"
    fail.write_text(
        json.dumps(
            {
                "stream_id": "lint",
                "passed": False,
                "checks": [{"check_id": "ruff.check", "passed": False}],
            },
        ),
        encoding="utf-8",
    )
    py = sys.executable
    good = subprocess.run([py, str(_AGG), str(ok)], capture_output=True, text=True, check=False)
    assert good.returncode == 0
    bad = subprocess.run([py, str(_AGG), str(ok), str(fail)], capture_output=True, text=True, check=False)
    assert bad.returncode == 1


def test_slice_gate_standards_step() -> None:
    from orchestrator.slice.gate import run_slice_gate_chain
    from orchestrator.slice.micro_slice import parse_slice_plan

    plan = parse_slice_plan({"slice_id": "s-std", "target_paths": ["a.py"]})
    result = run_slice_gate_chain(
        plan,
        verify_ok=True,
        critique_verdicts=["PASS"],
        tests_passed=True,
        standards_passed=False,
        standards_detail="bundle fail",
    )
    step = next(s for s in result.steps if s.name == "slice.standards")
    assert step.verdict == "FAIL"
    assert not result.passed
