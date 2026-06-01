"""Regenerate bundles/_shared.py from workflows/_shared exports."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WF = REPO / "packages/nimbusware_console/pages/config_tooling/workflows/_shared.py"
BUNDLES = REPO / "packages/nimbusware_console/pages/config_tooling/bundles/_shared.py"


def main() -> None:
    tree = ast.parse(WF.read_text(encoding="utf-8"))
    names = sorted(
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    )
    joined = ",\n    ".join(names)
    text = f'''"""Re-export workflow shared helpers for bundle pages."""

from nimbusware_console.pages.config_tooling.workflows._shared import (
    {joined},
)
'''
    BUNDLES.write_text(text, encoding="utf-8")
    print(f"wrote bundles/_shared.py ({len(names)} names)")


if __name__ == "__main__":
    main()
