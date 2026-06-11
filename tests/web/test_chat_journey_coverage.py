from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

_REPO = Path(__file__).resolve().parents[2]
_SCENARIOS = Path(__file__).resolve().parent / "chat_journey_scenarios.yaml"
_MIN_COVERAGE = 0.8


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_chat_journey_scenario_specs_exist() -> None:
    doc = _load(_SCENARIOS)
    rows = doc.get("scenarios") or {}
    assert isinstance(rows, dict) and rows
    for scenario_id, row in rows.items():
        rel = str((row or {}).get("spec") or "")
        spec = (_REPO / rel).resolve()
        assert spec.is_file(), f"{scenario_id} -> {rel}"


def test_chat_journey_scenarios_meet_eighty_percent_gate() -> None:
    doc = _load(_SCENARIOS)
    rows = doc.get("scenarios") or {}
    total = len(rows)
    assert total >= 5, "expected at least five Chat journey scenarios"
    covered = sum(
        1
        for row in rows.values()
        if isinstance(row, dict) and (_REPO / str(row.get("spec") or "")).resolve().is_file()
    )
    ratio = covered / total
    assert ratio >= _MIN_COVERAGE, (
        f"{covered}/{total} Chat journey scenarios wired ({ratio:.0%}); "
        f"need ≥{_MIN_COVERAGE:.0%} per §20.28.9"
    )
