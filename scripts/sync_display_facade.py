from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG_INIT = REPO / "packages/nimbusware_console/integrator_gate/__init__.py"
FACADE = REPO / "packages/nimbusware_console/integrator_gate_display.py"


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module or node.module == "__future__":
            continue
        for alias in node.names:
            if alias.name != "*":
                names.append(alias.asname or alias.name)
    return sorted(set(names))


def main() -> None:
    names = _imported_names(PKG_INIT)
    mod = "nimbusware_console.integrator_gate"
    body = f"from {mod} import (\n    " + ",\n    ".join(names) + ",\n)\n"
    FACADE.write_text(body, encoding="utf-8")
    print(f"wrote {len(names)} names to {FACADE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
