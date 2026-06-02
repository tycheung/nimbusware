from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_FLOORS_SCRIPT = _REPO / "scripts" / "coverage_package_floors.py"


def _load_floors_module():
    spec = importlib.util.spec_from_file_location("coverage_package_floors", _FLOORS_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_package_floors_include_core_contract_packages() -> None:
    text = _FLOORS_SCRIPT.read_text(encoding="utf-8")
    for pkg in (
        "agent_core",
        "hermes_store",
        "hermes_executor",
        "nimbusware_config",
        "nimbusware_projections",
    ):
        assert f'"{pkg}"' in text, f"missing package floor for {pkg}"


def test_package_floors_helper_aggregates_by_prefix() -> None:
    mod = _load_floors_module()
    report = {
        "files": {
            "packages/agent_core/models/events.py": {
                "summary": {"covered_lines": 90, "num_statements": 100},
            },
            "packages/agent_core/other.py": {
                "summary": {"covered_lines": 80, "num_statements": 100},
            },
        }
    }
    pct = mod._package_coverage_pct(report, "agent_core")
    assert pct is not None
    assert abs(pct - 85.0) < 0.01
