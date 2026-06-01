"""Add missing streamlit import to workflow consumers that use st without importing it."""

from __future__ import annotations

import ast
from pathlib import Path

WF = Path(__file__).resolve().parents[1] / "packages/nimbusware_console/pages/config_tooling/workflows"
IMPORT_LINE = "import streamlit as st\n"


def _uses_st(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "st":
                return True
    return False


def _has_st_import(text: str) -> bool:
    return "import streamlit as st" in text


def main() -> None:
    changed = 0
    for path in sorted(WF.rglob("*.py")):
        if path.name.startswith("_shared"):
            continue
        text = path.read_text(encoding="utf-8")
        if not _uses_st(path) or _has_st_import(text):
            continue
        lines = text.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from __future__"):
                insert_at = i + 1
                break
        if insert_at and insert_at < len(lines) and lines[insert_at] == "\n":
            insert_at += 1
        lines.insert(insert_at, "\n" + IMPORT_LINE)
        path.write_text("".join(lines), encoding="utf-8")
        print(path.relative_to(WF))
        changed += 1
    print(f"updated {changed} files")


if __name__ == "__main__":
    main()
