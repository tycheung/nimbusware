"""Scoped slice.implement (non-stub)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from hermes_orchestrator.micro_slice import parse_slice_plan
from hermes_orchestrator.slice_implement import execute_slice_implement, slice_implement_mode


def test_slice_implement_mode_default_scoped() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HERMES_SLICE_IMPLEMENT", None)
        assert slice_implement_mode() == "scoped"


def test_slice_implement_stub_mode() -> None:
    with patch.dict(os.environ, {"HERMES_SLICE_IMPLEMENT": "stub"}, clear=False):
        plan = parse_slice_plan(
            {
                "slice_id": "s1",
                "target_paths": ["packages/hermes_orchestrator/micro_slice.py"],
            },
        )
        root = Path(__file__).resolve().parents[1]
        result = execute_slice_implement(root, plan)
        assert result.mode == "stub"
        assert result.paths_touched == ()


def test_slice_implement_scoped_touches_existing_file() -> None:
    root = Path(__file__).resolve().parents[1]
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": ["packages/hermes_orchestrator/slice_implement.py"],
        },
    )
    with patch.dict(os.environ, {"HERMES_SLICE_IMPLEMENT": "scoped"}, clear=False):
        result = execute_slice_implement(root, plan, timeout_seconds=60.0)
    assert result.mode == "scoped"
    assert "slice_implement.py" in "".join(result.paths_touched)
