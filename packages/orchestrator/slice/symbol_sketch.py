from __future__ import annotations

import ast
from pathlib import Path


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def _top_level_symbols(tree: ast.Module) -> list[str]:
    lines: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}")
        elif isinstance(node, ast.FunctionDef):
            lines.append(f"def {node.name}")
        elif isinstance(node, ast.AsyncFunctionDef):
            lines.append(f"async def {node.name}")
    return lines


def _import_lines(tree: ast.Module) -> list[str]:
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = ", ".join(a.name for a in node.names)
            out.append(f"from {mod} import {names}")
    return out


def build_symbol_sketch_for_path(path: Path, *, max_lines: int = 30) -> str:
    if not path.is_file() or path.suffix != ".py":
        return ""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return f"# {path.name}: (unreadable)"
    doc = ast.get_docstring(tree) or ""
    doc_line = doc.splitlines()[0][:120] if doc else ""
    parts = [f"## {path.name}"]
    if doc_line:
        parts.append(f"doc: {doc_line}")
    syms = _top_level_symbols(tree)
    if syms:
        parts.append("symbols: " + ", ".join(syms[:20]))
    imports = _import_lines(tree)
    if imports:
        parts.append("imports:\n  " + "\n  ".join(imports[:15]))
    block = "\n".join(parts)
    lines = block.splitlines()
    if len(lines) > max_lines:
        block = "\n".join(lines[:max_lines]) + "\n..."
    return block


def build_symbol_sketch(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_chars: int = 3000,
) -> str:
    root = repo_root.resolve()
    blocks: list[str] = []
    for rel in target_paths:
        p = (root / rel).resolve()
        block = build_symbol_sketch_for_path(p)
        if block:
            blocks.append(block)
    if not blocks:
        return ""
    combined = "\n\n".join(blocks)
    return _truncate(combined, max_chars)
