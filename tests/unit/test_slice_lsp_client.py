from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestrator.slice.lsp_client import (
    _encode_message,
    build_lsp_symbol_sketch,
    build_symbol_sketch_with_lsp_fallback,
    format_document_symbols,
    read_lsp_message,
    resolve_lsp_command_argv,
)


def test_read_lsp_message_roundtrip() -> None:
    payload = {"jsonrpc": "2.0", "id": 1, "result": []}
    stream = io.BytesIO(_encode_message(payload))
    msg = read_lsp_message(stream)
    assert msg is not None
    assert msg["id"] == 1


def test_format_document_symbols_nested() -> None:
    symbols = [
        {
            "name": "Calc",
            "kind": 5,
            "range": {"start": {"line": 0}},
            "children": [{"name": "add", "kind": 6, "range": {"start": {"line": 1}}}],
        },
    ]
    text = format_document_symbols("calc.py", symbols)
    assert "class Calc" in text
    assert "method add" in text


def test_build_lsp_symbol_sketch_mocked() -> None:
    repo = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "swe_bench" / "repo"
    init_resp = _encode_message({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}})
    sym_resp = _encode_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": [{"name": "add", "kind": 12, "range": {"start": {"line": 0}}}],
        },
    )
    stdout = io.BytesIO(init_resp + sym_resp)

    proc = MagicMock()
    proc.stdin = io.BytesIO()
    proc.stdout = stdout
    proc.stderr = None
    proc.poll.return_value = None
    proc.wait.return_value = 0

    with patch(
        "orchestrator.slice.lsp_client.subprocess.Popen",
        return_value=proc,
    ):
        text, reason = build_lsp_symbol_sketch(repo, ("calc.py",), max_chars=2000)

    assert reason == ""
    assert "function add" in text


def test_resolve_lsp_command_env_override(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SLICE_LSP_COMMAND", "custom-langserver --stdio")
    argv = resolve_lsp_command_argv()
    assert argv == ["custom-langserver", "--stdio"]


def test_resolve_lsp_command_prefers_venv_scripts(monkeypatch, tmp_path: Path) -> None:
    scripts = tmp_path / "bin"
    scripts.mkdir()
    langserver = scripts / "pyright-langserver.exe"
    langserver.write_text("", encoding="utf-8")
    python = scripts / "python.exe"
    python.write_text("", encoding="utf-8")
    monkeypatch.delenv("NIMBUSWARE_SLICE_LSP_COMMAND", raising=False)
    monkeypatch.setattr("orchestrator.slice.lsp_client.shutil.which", lambda _name: None)
    monkeypatch.setattr(sys, "executable", str(python))
    argv = resolve_lsp_command_argv()
    assert argv == [str(langserver)]


def test_symbol_sketch_fallback_appends_import_graph(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from pkg import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("def foo() -> int:\n    return 1\n", encoding="utf-8")
    text, reason = build_symbol_sketch_with_lsp_fallback(
        tmp_path,
        ["pkg/a.py"],
        lsp_enabled=False,
        max_chars=4000,
    )
    assert reason == ""
    assert "pkg/a.py" in text or "a.py" in text
    assert "imports:" in text
    assert "pkg.a" in text


def test_lsp_fallback_expands_import_neighbors_two_hops(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from pkg import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("from pkg import c\n", encoding="utf-8")
    (pkg / "c.py").write_text("def chain() -> int:\n    return 3\n", encoding="utf-8")
    with patch(
        "orchestrator.slice.lsp_client.build_lsp_symbol_sketch",
        return_value=("", "disabled"),
    ):
        text, reason = build_symbol_sketch_with_lsp_fallback(
            tmp_path,
            ["pkg/a.py"],
            lsp_enabled=True,
            expand_neighbors=True,
            max_chars=4000,
        )
    assert reason in {"", "ast_fallback"}
    assert "imports:" in text
    assert "pkg.b" in text
