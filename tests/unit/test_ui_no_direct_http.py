from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MAKER_UI = _REPO / "packages" / "nimbusware_maker" / "ui"

_FORBIDDEN = frozenset(
    {
        "nimbusware_client.http",
        "nimbusware_client",
        "nimbusware_maker.api_client",
    },
)


def _module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module
    return None


def _violations(py_path: Path) -> list[str]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    rel = py_path.relative_to(_REPO)
    out: list[str] = []
    for node in ast.walk(tree):
        mod = _module_name(node)
        if mod is None:
            continue
        if mod in _FORBIDDEN or mod.startswith("nimbusware_client."):
            out.append(f"{rel}: imports {mod}")
    return out


def test_maker_ui_has_no_direct_http_client() -> None:
    violations: list[str] = []
    for py_path in sorted(_MAKER_UI.glob("*.py")):
        violations.extend(_violations(py_path))
    assert not violations, "Maker ui/ must call services/, not HTTP clients:\n" + "\n".join(
        violations,
    )
