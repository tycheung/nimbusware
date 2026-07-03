from __future__ import annotations

from pathlib import Path

from orchestrator.frontend_writer_stage import (
    discover_frontend_files,
    run_frontend_writer_stage,
)


def test_discover_frontend_files_finds_html(tmp_path: Path) -> None:
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text("<html></html>", encoding="utf-8")
    found = discover_frontend_files(tmp_path)
    assert any(p.name == "index.html" for p in found)


def test_run_frontend_writer_scaffolds_when_empty(tmp_path: Path) -> None:
    code, log, mode = run_frontend_writer_stage(tmp_path)
    assert code == 0
    assert mode == "scaffold"
    assert (tmp_path / "static" / "index.html").is_file()
    assert "scaffolded" in log


def test_run_frontend_writer_validates_existing(tmp_path: Path) -> None:
    (tmp_path / "app.js").write_text("console.log(1)", encoding="utf-8")
    code, log, mode = run_frontend_writer_stage(tmp_path)
    assert code == 0
    assert mode == "validate"
    assert "validated" in log
