from __future__ import annotations

from pathlib import Path

from agent_tools.risk_caps import PATCH_DEFAULT_CAPS, agent_risk_caps_from_run_rows
from orchestrator.micro_slice import micro_slice_count_for_run, parse_slice_plan
from orchestrator.patch_context import (
    apply_patch_stub_hotfix,
    implementation_path_from_failing_test,
    infer_patch_implementation_paths,
    maven_test_class_from_failing_test,
    normalize_patch_context,
    patch_auto_apply_allowed,
    patch_context_from_run_rows,
    resolve_patch_test_targets,
    work_type_from_run_rows,
)
from orchestrator.workflow_patch import (
    parse_patch_workflow_block,
    patch_effective_metadata,
)


def test_parse_patch_workflow_block_enabled() -> None:
    root = Path(__file__).resolve().parents[2]
    block = parse_patch_workflow_block(root, "patch")
    assert block.enabled is True
    assert block.auto_apply.max_loc == 40
    assert block.risk_caps is not None
    assert block.risk_caps.max_tool_steps == 12


def test_patch_effective_metadata() -> None:
    root = Path(__file__).resolve().parents[2]
    block = parse_patch_workflow_block(root, "patch")
    meta = patch_effective_metadata(block)
    assert meta["enabled"] is True
    assert meta["auto_apply_policy"]["max_files"] == 1


def test_normalize_patch_context() -> None:
    ctx = normalize_patch_context(
        {
            "target_paths": ["src/a.py"],
            "failing_test": "tests/test_a.py::test_x",
            "stack_trace": "AssertionError",
        },
    )
    assert ctx is not None
    assert ctx["failing_test"] == "tests/test_a.py::test_x"


def test_resolve_patch_test_targets_prefers_failing_test() -> None:
    targets = resolve_patch_test_targets(
        ("src/a.py",),
        {"failing_test": "tests/test_a.py::test_x"},
    )
    assert targets == ["tests/test_a.py::test_x"]


def test_patch_auto_apply_allowed() -> None:
    policy = {"max_loc": 40, "max_files": 1, "require_tests_passed": True}
    assert patch_auto_apply_allowed(
        policy=policy,
        files_changed=1,
        loc_changed=12,
        tests_passed=True,
        gate_passed=True,
    )
    assert not patch_auto_apply_allowed(
        policy=policy,
        files_changed=2,
        loc_changed=12,
        tests_passed=True,
        gate_passed=True,
    )


def test_micro_slice_count_patch_run() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {"work_type": "patch", "patch_effective": {"enabled": True}},
        },
    ]
    assert micro_slice_count_for_run(rows) == 1


def test_agent_risk_caps_from_run_rows() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "agent_tools_effective": {
                    "risk_caps": PATCH_DEFAULT_CAPS.to_metadata(),
                },
            },
        },
    ]
    caps = agent_risk_caps_from_run_rows(rows)
    assert caps.max_tool_steps == 12


def test_implementation_path_from_failing_test_go() -> None:
    path = implementation_path_from_failing_test("calculator_test.go", stack="go")
    assert path == "calculator.go"


def test_maven_test_class_from_failing_test() -> None:
    selector = maven_test_class_from_failing_test(
        "src/test/java/com/example/CalculatorTest.java",
    )
    assert selector == "com.example.CalculatorTest"


def test_patch_context_from_run_rows_uses_run_created_not_first_row() -> None:
    rows = [
        {
            "event_type": "stage.started",
            "metadata": {"patch_context": {"failing_test": "wrong"}},
        },
        {
            "event_type": "run.created",
            "metadata": {
                "patch_context": {"failing_test": "src/test/java/com/example/CalculatorTest.java"},
                "work_type": "patch",
            },
        },
    ]
    ctx = patch_context_from_run_rows(rows)
    assert ctx is not None
    assert ctx["failing_test"] == "src/test/java/com/example/CalculatorTest.java"
    assert work_type_from_run_rows(rows) == "patch"


def test_infer_patch_implementation_paths_from_go_fixture(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests/fixtures/repos/tiny_go_app"
    paths = infer_patch_implementation_paths(
        {"failing_test": "calculator_test.go"},
        fixture,
    )
    assert paths == ("calculator.go",)


def test_apply_patch_stub_hotfix_jvm_calculator(tmp_path: Path) -> None:
    ws = tmp_path / "tiny_jvm_app"
    target = ws / "src/main/java/com/example/Calculator.java"
    target.parent.mkdir(parents=True)
    target.write_text(
        "package com.example;\npublic final class Calculator {\n"
        "  public static int add(int a, int b) { return a + b + 1; }\n}\n",
        encoding="utf-8",
    )
    plan = parse_slice_plan(
        {
            "slice_id": "slice-1",
            "target_paths": ["src/main/java/com/example/Calculator.java"],
        },
    )
    rows = [
        {
            "event_type": "run.created",
            "metadata": {"work_type": "patch", "patch_effective": {"enabled": True}},
        },
    ]
    touched = apply_patch_stub_hotfix(ws, plan, rows)
    assert touched == ("src/main/java/com/example/Calculator.java",)
    assert "return a + b + 1" not in target.read_text(encoding="utf-8")
    assert "return a + b;" in target.read_text(encoding="utf-8")
