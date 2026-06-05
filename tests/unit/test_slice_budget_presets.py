from __future__ import annotations

from nimbusware_orchestrator.micro_slice_executor import slice_replan_max_for_run
from nimbusware_orchestrator.slice_budget_presets import (
    resolve_slice_budget_preset,
    slice_budget_preset,
)


def test_slice_budget_preset_values() -> None:
    tiny = slice_budget_preset("tiny")
    assert tiny.max_files == 1 and tiny.max_loc == 40 and tiny.replan_max == 1
    standard = slice_budget_preset("standard")
    assert standard.max_files == 3 and standard.max_loc == 120
    careful = slice_budget_preset("careful")
    assert careful.max_files == 2 and careful.replan_max == 5


def test_resolve_from_operator_settings() -> None:
    preset = resolve_slice_budget_preset(
        operator_settings={"NIMBUSWARE_SLICE_BUDGET_PRESET": "careful"},
    )
    assert preset.name == "careful"
    assert preset.max_loc == 80


def test_slice_replan_max_for_run_uses_frozen_metadata() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "micro_slice_effective": {
                    "enabled": True,
                    "replan_max": 5,
                    "max_files": 2,
                    "max_loc": 80,
                },
            },
        },
    ]
    assert slice_replan_max_for_run(rows) == 5
