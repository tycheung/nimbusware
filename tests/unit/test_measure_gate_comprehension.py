from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load_measure_gate_comprehension():
    path = _ROOT / "scripts" / "benchmarks" / "measure_gate_comprehension.py"
    spec = importlib.util.spec_from_file_location("measure_gate_comprehension", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["measure_gate_comprehension"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gate_comprehension_fixture_passes() -> None:
    mod = _load_measure_gate_comprehension()
    metrics = mod.measure_gate_comprehension(
        fixture_path=_ROOT / "benchmarks" / "gate_failure_comprehension_fixture.json",
    )
    assert metrics["ok"] is True
    assert float(metrics["fit_score"]) >= 0.8
