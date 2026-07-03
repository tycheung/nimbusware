from __future__ import annotations

from pathlib import Path

from orchestrator.workspace_layout import detect_workspace_layout


def test_detect_node_layout(tmp_path: Path) -> None:
    ws = tmp_path / "web"
    ws.mkdir()
    (ws / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (ws / "src").mkdir()
    (ws / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
    layout = detect_workspace_layout(ws)
    assert layout.stack == "node"
    assert "src" in layout.source_roots


def test_detect_rust_layout(tmp_path: Path) -> None:
    ws = tmp_path / "svc"
    ws.mkdir()
    (ws / "Cargo.toml").write_text('[package]\nname = "svc"\n', encoding="utf-8")
    (ws / "src").mkdir()
    (ws / "src" / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    layout = detect_workspace_layout(ws)
    assert layout.stack == "rust"
    assert "src" in layout.source_roots
