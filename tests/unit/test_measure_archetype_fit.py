from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _measure_module():
    path = _ROOT / "scripts" / "benchmarks" / "measure_archetype_fit.py"
    spec = importlib.util.spec_from_file_location("measure_archetype_fit", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["measure_archetype_fit"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_measure_archetype_fit_rubric_passes() -> None:
    mod = _measure_module()
    metrics = mod.measure_archetype_fit(repo_root=_ROOT)
    assert metrics["ok"] is True
    assert metrics["mode"] == "static_rubric"
    for name in ("safe_coding", "engineer"):
        row = metrics["archetypes"][name]
        assert row["fit_score"] >= 0.85
        assert row["checks_passed"] == row["checks_total"]
        assert row["missing"] == []
