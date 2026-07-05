from __future__ import annotations

from pathlib import Path

from standards.bundles.go_hygiene import check_file_loc, check_ignored_errors


def test_go_file_loc_flags_large_file(tmp_path: Path) -> None:
    path = tmp_path / "big.go"
    path.write_text("\n".join(["package main"] + ["// x"] * 500), encoding="utf-8")
    result = check_file_loc(workspace=tmp_path, params={"max_loc": 400})
    assert not result.passed
    assert "big.go" in result.detail


def test_go_ignored_errors_detects_blank_assign(tmp_path: Path) -> None:
    path = tmp_path / "main.go"
    path.write_text("package main\nfunc f() { _, _ = do() }\n", encoding="utf-8")
    result = check_ignored_errors(workspace=tmp_path, params={})
    assert not result.passed
