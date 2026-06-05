"""Repo map excerpt builder for slice context packets."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.slice_repo_map import (
    build_import_graph_excerpt,
    build_repo_map_excerpt,
    build_repo_tree_excerpt,
)


def test_repo_tree_skips_hidden_and_cache(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.pyc").write_text("", encoding="utf-8")
    tree = build_repo_tree_excerpt(tmp_path, max_lines=50)
    assert "src/" in tree
    assert "__pycache__" not in tree


def test_import_graph_for_target(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from pkg import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("def foo() -> int:\n    return 1\n", encoding="utf-8")
    graph = build_import_graph_excerpt(tmp_path, ["pkg/a.py"], max_edges=10)
    assert "pkg.a" in graph
    assert "->" in graph


def test_repo_map_respects_char_cap(tmp_path: Path) -> None:
    for i in range(20):
        (tmp_path / f"file_{i}.py").write_text(f"x{i} = {i}\n", encoding="utf-8")
    excerpt = build_repo_map_excerpt(tmp_path, ["file_0.py"], max_chars=200)
    assert len(excerpt) <= 203
