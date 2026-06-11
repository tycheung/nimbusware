from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WF = REPO / "packages/nimbusware_console/pages/config_tooling/workflows"
STAR = "from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403\n\n"
PREFIX = "nimbusware_console.pages.config_tooling.workflows._shared"


def _strip_shared_imports(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if path.name == "_shared.py" and path.parent == WF:
        return False
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    remove_ranges: list[tuple[int, int]] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(PREFIX):
            start = node.lineno - 1
            end = node.end_lineno or node.lineno
            remove_ranges.append((start, end))
    if not remove_ranges:
        return False
    for start, end in sorted(remove_ranges, reverse=True):
        del lines[start:end]
        if start < len(lines) and lines[start].strip() == "":
            del lines[start]
    new_text = "".join(lines)
    if STAR.strip() not in new_text:
        insert = 0
        out_lines = new_text.splitlines(keepends=True)
        for i, line in enumerate(out_lines):
            if line.startswith("from __future__"):
                insert = i + 1
                break
        if insert < len(out_lines) and out_lines[insert].strip() == "":
            insert += 1
        out_lines.insert(insert, "\n" + STAR)
        new_text = "".join(out_lines)
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    changed = 0
    for path in sorted(WF.rglob("*.py")):
        if _strip_shared_imports(path):
            print(path.relative_to(REPO))
            changed += 1
    print(f"reverted {changed} files")


if __name__ == "__main__":
    main()
