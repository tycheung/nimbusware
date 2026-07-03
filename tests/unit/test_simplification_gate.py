from __future__ import annotations

from pathlib import Path

from orchestrator.critique.simplification_gate import delete_with_tests_allowed


def test_delete_with_tests_requires_tests_dir(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    allowed, detail = delete_with_tests_allowed(ws, ("orphan.py",))
    assert allowed is False
    assert detail == "missing_tests_dir"


def test_delete_with_tests_passes_when_pytest_green(tmp_path: Path) -> None:
    ws = tmp_path / "app"
    ws.mkdir()
    (ws / "main.py").write_text("x = 1\n", encoding="utf-8")
    tests = ws / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    allowed, detail = delete_with_tests_allowed(ws, ("main.py",))
    assert allowed is True
    assert detail == "tests_pass"
