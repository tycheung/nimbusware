from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

import pytest

COMPOSITE_CONTRACT_MODULES: tuple[str, ...] = (
    "unit.test_anti_deadlock_helpers_composite_contract",
    "unit.test_critique_gate_fail_findings_composite_contract",
    "unit.test_critique_routing_quartet_composite_contract",
    "unit.test_list_runs_query_helpers_composite_contract",
    "unit.test_runs_list_composite_contract",
    "unit.test_read_models_composite_contract",
    "unit.test_runs_list_wire_format_composite_contract",
    "unit.test_scraper_artifact_retention_composite_contract",
    "unit.test_security_scan_metadata_siblings_composite_contract",
    "unit.test_strictness_context_critique_seam_composite_contract",
    "unit.test_thresholds_loader_composite_contract",
    "unit.test_timeline_summary_quintet_composite_contract",
)


def assert_contract(actual: Any, expected: Any, *, label: str) -> None:
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def assert_contract_predicate(actual: Any, predicate: Callable[[Any], bool], *, label: str) -> None:
    assert predicate(actual), f"{label}: predicate failed for {actual!r}"


@pytest.mark.parametrize("module_name", COMPOSITE_CONTRACT_MODULES)
def test_composite_contract_module_importable(module_name: str) -> None:
    importlib.import_module(module_name)
