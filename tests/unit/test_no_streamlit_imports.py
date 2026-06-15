from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCAN_ROOTS = (
    _REPO / "packages",
    _REPO / "tests",
    _REPO / "scripts",
)


def _is_forbidden(module: str) -> bool:
    return module == "streamlit" or module.startswith("streamlit.")


def _scan_file(path: Path) -> list[str]:
    rel = path.relative_to(_REPO).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden(alias.name):
                    hits.append(f"{rel}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if _is_forbidden(node.module):
                hits.append(f"{rel}: from {node.module}")
    return hits


def test_no_streamlit_imports() -> None:
    offenders: list[str] = []
    for root in _SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            offenders.extend(_scan_file(path))
    assert not offenders, "Streamlit imports remain:\n" + "\n".join(offenders)
