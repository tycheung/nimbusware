from __future__ import annotations

import ast
import re

_TS_DECL = re.compile(
    r"^\s*(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?class\s+(\w+)",
    re.MULTILINE,
)
_TS_FUNC = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
    re.MULTILINE,
)
_TS_METHOD = re.compile(
    r"^\s*(?:public\s+|private\s+|protected\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::|\{)",
    re.MULTILINE,
)
_GO_DECL = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.MULTILINE)
_GO_TYPE = re.compile(r"^type\s+(\w+)\s+(?:struct|interface)\b", re.MULTILINE)


def typescript_file_outline(source: str, *, rel_path: str = "") -> str:
    lines: list[str] = [f"// outline: {rel_path or 'module'}"]
    seen: set[str] = set()
    for rx in (_TS_DECL, _TS_FUNC, _TS_METHOD):
        for match in rx.finditer(source):
            name = match.group(1)
            if name in seen or name in {"constructor"}:
                continue
            seen.add(name)
            prefix = "class" if rx is _TS_DECL else "function"
            if rx is _TS_METHOD and prefix == "function":
                prefix = "method"
            lines.append(f"{prefix} {name}(...)")
            if len(lines) >= 120:
                break
    return "\n".join(lines)


def go_file_outline(source: str, *, rel_path: str = "") -> str:
    lines: list[str] = [f"// outline: {rel_path or 'module'}"]
    for rx in (_GO_TYPE, _GO_DECL):
        for match in rx.finditer(source):
            kind = "type" if rx is _GO_TYPE else "func"
            lines.append(f"{kind} {match.group(1)}(...)")
            if len(lines) >= 120:
                break
    return "\n".join(lines)


def file_outline(source: str, *, rel_path: str) -> str:
    norm = rel_path.replace("\\", "/").lower()
    if norm.endswith(".py"):
        return python_file_outline(source, rel_path=rel_path)
    if norm.endswith((".ts", ".tsx", ".js", ".jsx", ".mts", ".cts")):
        return typescript_file_outline(source, rel_path=rel_path)
    if norm.endswith(".go"):
        return go_file_outline(source, rel_path=rel_path)
    return python_file_outline(source, rel_path=rel_path)


def python_file_outline(source: str, *, rel_path: str = "") -> str:
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


def python_file_digest(source: str, *, rel_path: str = "") -> str:
    outline = file_outline(source, rel_path=rel_path)
    lines = [line for line in outline.splitlines() if line.strip()]
    return "\n".join(lines[:80])


def read_mode_for_file(
    rel_path: str,
    *,
    line_count: int,
    in_slice_targets: bool,
    outline_threshold: int | None = None,
    digest_threshold: int | None = None,
) -> str:
    threshold = outline_threshold if outline_threshold is not None else _outline_loc_threshold()
    digest_at = (
        digest_threshold if digest_threshold is not None else max(threshold * 2, threshold + 200)
    )
    if in_slice_targets:
        return "full"
    outline_exts = (".py", ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".go")
    if rel_path.endswith(outline_exts):
        if line_count >= digest_at:
            return "digest"
        if line_count >= threshold:
            return "outline"
    return "full"


def _outline_loc_threshold() -> int:
    from env.env_flags import nimbusware_read_outline_min_lines

    return nimbusware_read_outline_min_lines()
