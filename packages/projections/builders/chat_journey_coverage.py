from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root

_JOURNEY_SLO_TARGET = 0.80


def chat_journey_scenarios_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "tests" / "web" / "chat_journey_scenarios.yaml"


def build_chat_journey_coverage(repo_root: Path | None = None) -> dict[str, Any]:
    path = chat_journey_scenarios_path(repo_root)
    if not path.is_file():
        return {
            "scenario_count": 0,
            "wired_count": 0,
            "coverage_rate": None,
            "target_rate": _JOURNEY_SLO_TARGET,
            "meets_target": False,
            "scenarios": {},
        }
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = doc.get("scenarios") or {}
    root = repo_root or find_repo_root()
    wired: dict[str, bool] = {}
    for scenario_id, row in rows.items():
        if not isinstance(row, dict):
            wired[str(scenario_id)] = False
            continue
        rel = str(row.get("spec") or "")
        wired[str(scenario_id)] = bool(rel and (root / rel).resolve().is_file())
    total = len(wired)
    covered = sum(1 for ok in wired.values() if ok)
    rate = covered / total if total else None
    return {
        "scenario_count": total,
        "wired_count": covered,
        "coverage_rate": rate,
        "target_rate": _JOURNEY_SLO_TARGET,
        "meets_target": rate is not None and rate >= _JOURNEY_SLO_TARGET,
        "scenarios": wired,
    }
