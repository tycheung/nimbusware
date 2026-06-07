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


def _package_for_path(repo_root: Path, path: Path) -> str | None:
    mod = _module_name_for_path(repo_root, path)
    if not mod:
        return None
    if path.name == "__init__.py":
        return mod
    parts = mod.split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def _resolve_relative_module(package: str | None, level: int, module: str | None) -> str | None:
    if level <= 0:
        return module
    if not package:
        return None
    parts = package.split(".")
    if level > len(parts):
        return None
    anchor = parts[: len(parts) - level + 1]
    if module:
        anchor.extend(module.split("."))
    return ".".join(anchor) if anchor else None


def _imports_resolved(repo_root: Path, path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    package = _package_for_path(repo_root, path)
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative_module(package, node.level, node.module)
            if not node.names:
                if resolved:
                    mods.append(resolved)
                continue
            for alias in node.names:
                if alias.name == "*":
                    if resolved:
                        mods.append(resolved)
                    continue
                if resolved:
                    mods.append(f"{resolved}.{alias.name}")
                elif node.level == 0 and alias.name:
                    mods.append(alias.name)
    return mods


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
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if not node.names:
                if base:
                    mods.append(base.split(".")[0])
                continue
            for alias in node.names:
                if alias.name == "*":
                    if base:
                        mods.append(base)
                    continue
                if base:
                    mods.append(f"{base}.{alias.name}")
                else:
                    mods.append(alias.name.split(".")[0])
    return mods


def expand_target_paths(
    repo_root: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    max_neighbors: int = 3,
) -> tuple[str, ...]:
    """Return target paths plus capped one-hop import neighbors under repo_root."""
    if max_neighbors <= 0:
        return tuple(str(p).replace("\\", "/") for p in target_paths)
    root = repo_root.resolve()
    ordered: list[str] = []
    seen: set[str] = set()

    def add(rel: str) -> None:
        norm = rel.replace("\\", "/")
        if norm not in seen:
            seen.add(norm)
            ordered.append(norm)

    for rel in target_paths:
        add(str(rel))

    target_modules: dict[str, Path] = {}
    for rel in ordered:
        path = (root / rel).resolve()
        if not path.is_file() or path.suffix != ".py":
            continue
        mod = _module_name_for_path(root, path)
        if mod:
            target_modules[mod] = path

    extras: list[str] = []
    for path in target_modules.values():
        for imp in _imports_resolved(root, path):
            dest = _resolve_import_to_path(root, imp)
            if dest is None:
                continue
            try:
                rel_dest = str(dest.relative_to(root)).replace("\\", "/")
            except ValueError:
                continue
            if rel_dest not in seen:
                extras.append(rel_dest)
        if len(extras) >= max_neighbors:
            break

    if len(extras) < max_neighbors:
        for other in root.rglob("*.py"):
            if len(extras) >= max_neighbors:
                break
            if any(part in _SKIP_DIR_NAMES for part in other.parts):
                continue
            other_mod = _module_name_for_path(root, other)
            if not other_mod or other_mod in target_modules:
                continue
            for imp in _imports_resolved(root, other):
                for tmod in target_modules:
                    if imp == tmod.split(".")[0] or imp.startswith(tmod):
                        try:
                            rel_other = str(other.relative_to(root)).replace("\\", "/")
                        except ValueError:
                            continue
                        if rel_other not in seen and rel_other not in extras:
                            extras.append(rel_other)
                        break
            if len(extras) >= max_neighbors:
                break

    for rel in extras[:max_neighbors]:
        add(rel)
    return tuple(ordered)


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
        for imp in _imports_resolved(root, path):
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
