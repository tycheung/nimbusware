from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

from hermes_orchestrator.slice_lsp_client import (
    _encode_message,
    build_lsp_symbol_sketch,
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
        "hermes_orchestrator.slice_lsp_client.subprocess.Popen",
        return_value=proc,
    ):
        text, reason = build_lsp_symbol_sketch(repo, ("calc.py",), max_chars=2000)

    assert reason == ""
    assert "function add" in text


def test_resolve_lsp_command_env_override(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_SLICE_LSP_COMMAND", "custom-langserver --stdio")
    argv = resolve_lsp_command_argv()
    assert argv == ["custom-langserver", "--stdio"]
