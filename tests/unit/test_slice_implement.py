from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from env import find_repo_root
from orchestrator.slice.implement import execute_slice_implement, slice_implement_mode
from orchestrator.slice.micro_slice import parse_slice_plan


def test_slice_implement_mode_default_scoped() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NIMBUSWARE_SLICE_IMPLEMENT", None)
        assert slice_implement_mode() == "scoped"


def test_slice_implement_stub_mode() -> None:
    with patch.dict(os.environ, {"NIMBUSWARE_SLICE_IMPLEMENT": "stub"}, clear=False):
        plan = parse_slice_plan(
            {
                "slice_id": "s1",
                "target_paths": ["packages/orchestrator/slice/micro_slice.py"],
            },
        )
        root = find_repo_root(start=Path(__file__).resolve().parents[1])
        result = execute_slice_implement(root, plan)
        assert result.mode == "stub"
        assert result.paths_touched == ()


def test_slice_implement_scoped_touches_existing_file() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": ["packages/orchestrator/slice/implement.py"],
        },
    )
    with patch.dict(os.environ, {"NIMBUSWARE_SLICE_IMPLEMENT": "scoped"}, clear=False):
        result = execute_slice_implement(root, plan, timeout_seconds=60.0)
    assert result.mode == "scoped"
    assert "slice/implement.py" in "".join(result.paths_touched)


def test_slice_implement_scoped_skips_ruff_for_non_python_targets(tmp_path: Path) -> None:
    ws = tmp_path / "jvm"
    target = ws / "src/main/java/com/example/Calculator.java"
    target.parent.mkdir(parents=True)
    target.write_text(
        "package com.example;\npublic final class Calculator {\n"
        "  public static int add(int a, int b) { return a + b; }\n}\n",
        encoding="utf-8",
    )
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": ["src/main/java/com/example/Calculator.java"],
        },
    )
    with patch.dict(os.environ, {"NIMBUSWARE_SLICE_IMPLEMENT": "scoped"}, clear=False):
        result = execute_slice_implement(ws, plan, timeout_seconds=30.0)
    assert result.mode == "scoped"
    assert result.exit_code == 0
    assert "non-Python" in result.log
