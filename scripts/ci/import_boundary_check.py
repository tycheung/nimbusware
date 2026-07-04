#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "packages" / "api"
ORCHESTRATOR_ROOT = ROOT / "packages" / "orchestrator"


def module_level_import_prefixes(path: Path, prefix: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == prefix or alias.name.startswith(f"{prefix}."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == prefix or mod.startswith(f"{prefix}."):
                hits.append(mod)
    return hits


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts and path.is_file()
    )


def collect_violations(
    *,
    orchestrator_root: Path | None = None,
) -> list[str]:
    orchestrator_root = orchestrator_root or ORCHESTRATOR_ROOT
    violations: list[str] = []

    for path in _iter_python_files(orchestrator_root):
        hits = module_level_import_prefixes(path, "api")
        if hits:
            rel = path.relative_to(orchestrator_root.parent)
            violations.append(f"{rel.as_posix()}: {hits}")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print(
            "import boundary violations (orchestrator must not import api at module level):",
            file=sys.stderr,
        )
        for item in violations:
            print(f"  {item}", file=sys.stderr)
        return 1
    print("import boundary check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
