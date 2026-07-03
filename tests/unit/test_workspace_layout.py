from __future__ import annotations

from pathlib import Path

from orchestrator.workspace_layout import detect_workspace_layout


def test_detect_src_layout(tmp_path: Path) -> None:
    ws = tmp_path / "app"
    ws.mkdir()
    (ws / "src").mkdir()
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (ws / "tests").mkdir()
    (ws / "tests" / "test_main.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (ws / "pyproject.toml").write_text("[tool.coverage.run]\nfail_under = 80\n", encoding="utf-8")
    layout = detect_workspace_layout(ws)
    assert "src" in layout.source_roots
    assert "tests" in layout.test_roots
    assert layout.coverage_floor == 0.8


def test_detect_packages_layout() -> None:
    root = Path(__file__).resolve().parents[2]
    layout = detect_workspace_layout(root)
    assert "packages" in layout.source_roots
    assert "tests" in layout.test_roots
    assert layout.has_pyproject is True
