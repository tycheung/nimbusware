from __future__ import annotations

import ast
from pathlib import Path


def python_file_outline(source: str, *, rel_path: str = "") -> str:
    """Return signatures and class boundaries for a Python module."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"# outline unavailable ({rel_path}): {exc}"
    lines: list[str] = [f"# outline: {rel_path or 'module'}"]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}(...):")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    sig = ", ".join(args[:6])
                    prefix = "async def" if isinstance(item, ast.AsyncFunctionDef) else "def"
                    lines.append(f"  {prefix} {item.name}({sig})")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            sig = ", ".join(args[:8])
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            lines.append(f"{prefix} {node.name}({sig})")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.append(ast.get_source_segment(source, node) or "import ...")
    return "\n".join(lines[:120])


def read_mode_for_file(
    rel_path: str,
    *,
    line_count: int,
    in_slice_targets: bool,
    outline_threshold: int | None = None,
) -> str:
    threshold = outline_threshold if outline_threshold is not None else _outline_loc_threshold()
    if in_slice_targets:
        return "full"
    if rel_path.endswith(".py") and line_count >= threshold:
        return "outline"
    return "full"


def _outline_loc_threshold() -> int:
    from env.env_flags import nimbusware_read_outline_min_lines

    return nimbusware_read_outline_min_lines()
