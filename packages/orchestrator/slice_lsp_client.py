from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from env.env_flags import (
    nimbusware_slice_lsp_command,
    nimbusware_slice_lsp_timeout_sec,
)

_LOG = logging.getLogger(__name__)

_SYMBOL_KIND: dict[int, str] = {
    1: "file",
    2: "module",
    3: "namespace",
    4: "package",
    5: "class",
    6: "method",
    7: "property",
    8: "field",
    9: "constructor",
    10: "enum",
    11: "interface",
    12: "function",
    13: "variable",
    14: "constant",
}


def _encode_message(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _read_content_length(stream: Any) -> int:
    length = 0
    while True:
        line = stream.readline()
        if not line:
            return 0
        if line in (b"\r\n", b"\n"):
            break
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    return length


def read_lsp_message(stream: Any) -> dict[str, Any] | None:
    """Read one LSP JSON-RPC message from a byte stream (for tests and client)."""
    n = _read_content_length(stream)
    if n <= 0:
        return None
    raw = stream.read(n)
    if not raw:
        return None
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("LSP payload must be a JSON object")
    return data


def write_lsp_message(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(_encode_message(payload))
    stream.flush()


def _venv_langserver_candidates() -> Sequence[Path]:
    scripts = Path(sys.executable).resolve().parent
    names = ("pyright-langserver", "pyright-langserver.exe", "pyright-langserver.cmd")
    return [scripts / name for name in names]


def resolve_lsp_command_argv() -> list[str] | None:
    override = nimbusware_slice_lsp_command()
    if override:
        return shlex.split(override, posix=os.name != "nt")
    for candidate in _venv_langserver_candidates():
        if candidate.is_file():
            return [str(candidate)]
    for name in ("pyright-langserver", "pyright-langserver.cmd"):
        found = shutil.which(name)
        if found:
            return [found]
    npx = shutil.which("npx")
    if npx:
        return [npx, "pyright-langserver"]
    return None


def format_document_symbols(
    rel_path: str,
    symbols: list[dict[str, Any]],
    *,
    max_symbols: int = 40,
) -> str:
    lines: list[str] = [f"## {rel_path} (lsp)"]
    count = 0

    def walk(nodes: list[dict[str, Any]], depth: int = 0) -> None:
        nonlocal count
        for node in nodes:
            if count >= max_symbols:
                return
            name = str(node.get("name") or "").strip()
            if not name:
                continue
            kind = _SYMBOL_KIND.get(int(node.get("kind") or 0), "symbol")
            rng = node.get("range") or {}
            start = rng.get("start") or {}
            line = int(start.get("line", 0)) + 1
            indent = "  " * depth
            lines.append(f"{indent}{kind} {name} @L{line}")
            count += 1
            children = node.get("children")
            if isinstance(children, list) and children:
                walk(children, depth + 1)

    walk(symbols)
    return "\n".join(lines)


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _request(
    proc: subprocess.Popen[bytes],
    *,
    msg_id: int,
    method: str,
    params: dict[str, Any] | None = None,
    timeout_sec: float,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        payload["params"] = params
    write_lsp_message(proc.stdin, payload)
    deadline = timeout_sec
    import time

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < deadline:
        if proc.stdout is None:
            return None
        msg = read_lsp_message(proc.stdout)
        if msg is None:
            continue
        if msg.get("id") == msg_id:
            return msg
    return None


def fetch_document_symbols(
    repo_root: Path,
    rel_path: str,
    *,
    command_argv: list[str] | None = None,
    timeout_sec: float | None = None,
) -> tuple[list[dict[str, Any]], str]:
    root = repo_root.resolve()
    path = (root / rel_path).resolve()
    if not path.is_file() or path.suffix != ".py":
        return [], "not_a_python_file"
    argv = command_argv or resolve_lsp_command_argv()
    if not argv:
        return [], "langserver_missing"
    timeout = timeout_sec if timeout_sec is not None else float(nimbusware_slice_lsp_timeout_sec())
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"read_error:{exc}"

    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=str(root),
    )
    if proc.stdin is None or proc.stdout is None:
        proc.kill()
        return [], "stdio_unavailable"

    try:
        init = _request(
            proc,
            msg_id=1,
            method="initialize",
            params={
                "processId": os.getpid(),
                "rootUri": _file_uri(root),
                "capabilities": {},
            },
            timeout_sec=timeout,
        )
        if not init or "error" in init:
            return [], "initialize_failed"
        write_lsp_message(
            proc.stdin,
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        )
        uri = _file_uri(path)
        write_lsp_message(
            proc.stdin,
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "python",
                        "version": 1,
                        "text": text,
                    },
                },
            },
        )
        sym_resp = _request(
            proc,
            msg_id=2,
            method="textDocument/documentSymbol",
            params={"textDocument": {"uri": uri}},
            timeout_sec=timeout,
        )
        if not sym_resp or "error" in sym_resp:
            return [], "document_symbol_failed"
        result = sym_resp.get("result")
        if not isinstance(result, list):
            return [], "document_symbol_empty"
        return result, ""
    except (OSError, json.JSONDecodeError, ValueError, subprocess.SubprocessError) as exc:
        _LOG.debug("LSP symbol fetch failed for %s: %s", rel_path, exc)
        return [], f"lsp_error:{type(exc).__name__}"
    finally:
        try:
            write_lsp_message(proc.stdin, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
            write_lsp_message(proc.stdin, {"jsonrpc": "2.0", "method": "exit"})
        except OSError:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def build_lsp_symbol_sketch(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_chars: int = 3000,
) -> tuple[str, str]:
    blocks: list[str] = []
    last_reason = ""
    for rel in target_paths:
        symbols, reason = fetch_document_symbols(repo_root, str(rel))
        if reason:
            last_reason = reason
            continue
        if symbols:
            blocks.append(format_document_symbols(str(rel), symbols))
    if not blocks:
        return "", last_reason or "no_symbols"
    combined = "\n\n".join(blocks)
    if max_chars > 0 and len(combined) > max_chars:
        combined = combined[: max(0, max_chars - 3)] + "..."
    return combined, ""


def build_symbol_sketch_with_lsp_fallback(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_chars: int = 3000,
    lsp_enabled: bool = True,
    expand_neighbors: bool = True,
) -> tuple[str, str]:
    """Try LSP sketch when enabled; fall back to AST builder with reason metadata."""
    from orchestrator.slice_repo_map import (
        build_import_graph_excerpt,
        expand_target_paths,
    )
    from orchestrator.slice_symbol_sketch import build_symbol_sketch

    paths: tuple[str, ...] | list[str] = target_paths
    if expand_neighbors:
        paths = expand_target_paths(repo_root, target_paths, max_hops=2)

    if lsp_enabled:
        lsp_text, reason = build_lsp_symbol_sketch(
            repo_root,
            paths,
            max_chars=max_chars,
        )
        if lsp_text:
            graph = build_import_graph_excerpt(repo_root, target_paths, max_edges=12)
            if graph:
                combined = f"{lsp_text}\n\n{graph}"
                if max_chars > 0 and len(combined) > max_chars:
                    combined = combined[: max(0, max_chars - 3)] + "..."
                return combined, ""
        if reason:
            _LOG.debug("slice LSP fallback: %s", reason)
    ast_text = build_symbol_sketch(repo_root, paths, max_chars=max_chars)
    if ast_text:
        graph = build_import_graph_excerpt(repo_root, target_paths, max_edges=12)
        if graph:
            combined = f"{ast_text}\n\n{graph}"
            if max_chars > 0 and len(combined) > max_chars:
                combined = combined[: max(0, max_chars - 3)] + "..."
            ast_text = combined
    fallback_reason = "ast_fallback" if lsp_enabled else ""
    return ast_text, fallback_reason
