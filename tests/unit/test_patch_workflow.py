from __future__ import annotations

from pathlib import Path

from nimbusware_agent_tools.risk_caps import PATCH_DEFAULT_CAPS, agent_risk_caps_from_run_rows
from nimbusware_orchestrator.micro_slice import micro_slice_count_for_run
from nimbusware_orchestrator.patch_context import (
    implementation_path_from_failing_test,
    infer_patch_implementation_paths,
    normalize_patch_context,
    patch_auto_apply_allowed,
    resolve_patch_test_targets,
)
from nimbusware_orchestrator.workflow_patch import (
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


def test_infer_patch_implementation_paths_from_go_fixture(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests/fixtures/repos/tiny_go_app"
    paths = infer_patch_implementation_paths(
        {"failing_test": "calculator_test.go"},
        fixture,
    )
    assert paths == ("calculator.go",)
