"""Build capped repo tree + import-graph excerpts for slice context packets."""

from __future__ import annotations

import ast
from pathlib import Path

_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".tox",
        ".eggs",
    },
)


def _should_skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.startswith(".")


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def build_repo_tree_excerpt(
    repo_root: Path,
    *,
    max_lines: int = 80,
    max_depth: int = 3,
) -> str:
    """Depth-limited directory tree under repo_root."""
    if max_lines <= 0:
        return ""
    root = repo_root.resolve()
    lines: list[str] = [f"{root.name}/"]

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if len(lines) >= max_lines or depth > max_depth:
            return
        try:
            children = sorted(
                [p for p in dir_path.iterdir() if not _should_skip_dir(p.name)],
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return
        for i, child in enumerate(children):
            if len(lines) >= max_lines:
                break
            last = i == len(children) - 1
            branch = "└── " if last else "├── "
            lines.append(f"{prefix}{branch}{child.name}{'/' if child.is_dir() else ''}")
            if child.is_dir() and depth < max_depth:
                extension = "    " if last else "│   "
                walk(child, prefix + extension, depth + 1)

    walk(root, "", 0)
    return "\n".join(lines)


def _module_name_for_path(repo_root: Path, path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return ".".join(parts) if parts else None


def _resolve_import_to_path(repo_root: Path, module: str, *, level: int = 0) -> Path | None:
    root = repo_root.resolve()
    if level > 0:
        return None
    candidate = root.joinpath(*module.split(".")).with_suffix(".py")
    if candidate.is_file():
        return candidate
    init_candidate = root.joinpath(*module.split("."), "__init__.py")
    if init_candidate.is_file():
        return init_candidate
    return None


def _imports_in_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module.split(".")[0])
    return mods


def build_import_graph_excerpt(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_edges: int = 40,
) -> str:
    """One-hop import edges for target .py paths within repo_root."""
    root = repo_root.resolve()
    edges: list[str] = []
    seen_edges: set[str] = set()
    target_modules: dict[str, Path] = {}

    for rel in target_paths:
        p = (root / rel).resolve()
        if not p.is_file() or p.suffix != ".py":
            continue
        mod = _module_name_for_path(root, p)
        if mod:
            target_modules[mod] = p

    for mod, path in target_modules.items():
        for imp in _imports_in_file(path):
            dest = _resolve_import_to_path(root, imp)
            if dest is None:
                continue
            dest_mod = _module_name_for_path(root, dest)
            if not dest_mod:
                continue
            edge = f"{mod} -> {dest_mod}"
            if edge not in seen_edges:
                seen_edges.add(edge)
                edges.append(edge)
            if len(edges) >= max_edges:
                break
        if len(edges) >= max_edges:
            break

    for other in root.rglob("*.py"):
        if len(edges) >= max_edges:
            break
        if any(part in _SKIP_DIR_NAMES for part in other.parts):
            continue
        other_mod = _module_name_for_path(root, other)
        if not other_mod or other_mod in target_modules:
            continue
        for imp in _imports_in_file(other):
            for tmod in target_modules:
                if imp == tmod.split(".")[0] or imp.startswith(tmod):
                    edge = f"{other_mod} -> {tmod}"
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        edges.append(edge)
                    break
        if len(edges) >= max_edges:
            break

    if not edges:
        return ""
    return "imports:\n" + "\n".join(edges[:max_edges])


def build_repo_map_excerpt(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_chars: int | None = None,
    max_tree_lines: int = 80,
    max_edges: int = 40,
) -> str:
    """Concatenate tree + import graph and apply char cap."""
    tree = build_repo_tree_excerpt(repo_root, max_lines=max_tree_lines)
    graph = build_import_graph_excerpt(repo_root, target_paths, max_edges=max_edges)
    parts = [p for p in (tree, graph) if p]
    if not parts:
        return ""
    combined = "\n\n".join(parts)
    if max_chars is not None and max_chars > 0:
        return _truncate(combined, max_chars)
    return combined
