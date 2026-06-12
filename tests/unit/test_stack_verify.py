from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.micro_slice_verify import _workspace_stack, run_slice_verify_and_test
from nimbusware_orchestrator.slice_gate import map_paths_to_test_targets

_REPO = Path(__file__).resolve().parents[2]


def test_map_paths_to_test_targets_go() -> None:
    targets = map_paths_to_test_targets(("calculator.go",))
    assert targets == ["calculator_test.go"]


def test_map_paths_to_test_targets_jvm() -> None:
    targets = map_paths_to_test_targets(
        ("src/main/java/com/example/Calculator.java",),
    )
    assert targets == ["src/test/java/com/example/CalculatorTest.java"]


def test_workspace_stack_detection() -> None:
    assert _workspace_stack(_REPO / "tests/fixtures/repos/tiny_go_app") == "go"
    assert _workspace_stack(_REPO / "tests/fixtures/repos/tiny_jvm_app") == "jvm"
    assert _workspace_stack(_REPO / "tests/fixtures/repos/tiny_python_app") == "python"


def test_run_slice_verify_skips_ruff_for_go(tmp_path: Path) -> None:
    ws = tmp_path / "go-ws"
    ws.mkdir()
    (ws / "go.mod").write_text("module example.com/fix\n\ngo 1.21\n", encoding="utf-8")
    (ws / "main.go").write_text("package main\nfunc main() {}\n", encoding="utf-8")
    plan = SlicePlan(slice_id="s1", target_paths=("main.go",), rationale="fix")
    verify_ok, log, tests_passed, _ = run_slice_verify_and_test(ws, plan, timeout_seconds=30.0)
    assert "ruff skipped" in log
    assert verify_ok is True
