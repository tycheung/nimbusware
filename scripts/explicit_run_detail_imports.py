"""Build explicit re-exports for run_detail import barrels."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_DETAIL = REPO / "packages/nimbusware_console/pages/run_detail"


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    names.append(alias.asname or alias.name)
    return sorted(set(names))


def _write_explicit_init(pkg_dir: Path, submodule_files: list[str]) -> None:
    blocks: list[str] = ["from __future__ import annotations", ""]
    all_names: list[str] = []
    for rel in submodule_files:
        mod = rel.removesuffix(".py").replace("/", ".")
        names = _imported_names(pkg_dir / rel)
        all_names.extend(names)
        joined = ",\n    ".join(names)
        blocks.append(f"from nimbusware_console.pages.run_detail.{pkg_dir.name}.{mod} import (")
        blocks.append(f"    {joined},")
        blocks.append(")")
        blocks.append("")
    (pkg_dir / "__init__.py").write_text("\n".join(blocks) + "\n", encoding="utf-8")
    print(f"wrote {pkg_dir.name}/__init__.py ({len(all_names)} names)")


def _write_barrel(path: Path, sources: list[tuple[str, Path]]) -> None:
    blocks = ["from __future__ import annotations", ""]
    for label, src in sources:
        names = _imported_names(src) if src.suffix == ".py" else _imported_names(src / "__init__.py")
        if src.is_dir():
            mod = f"nimbusware_console.pages.run_detail.{src.name}"
        else:
            mod = f"nimbusware_console.pages.run_detail.{src.stem}"
        joined = ",\n    ".join(names)
        blocks.append(f"from {mod} import (")
        blocks.append(f"    {joined},")
        blocks.append(")")
        blocks.append("")
    if path.name == "_imports.py":
        blocks.extend(
            [
                "import os",
                "from pathlib import Path",
                "",
                '_iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()',
                "",
            ]
        )
    path.write_text("\n".join(blocks), encoding="utf-8")
    print(f"wrote {path.name}")


def main() -> None:
    display_a_dir = RUN_DETAIL / "_imports_display_a"
    _write_explicit_init(
        display_a_dir,
        ["agent_through_escalation.py", "findings_through_persona.py"],
    )
    _write_barrel(
        RUN_DETAIL / "_imports_display_a.py",
        [("display_a", display_a_dir)],
    )
    _write_barrel(
        RUN_DETAIL / "_imports.py",
        [
            ("common", RUN_DETAIL / "_imports_common.py"),
            ("display_a", RUN_DETAIL / "_imports_display_a.py"),
            ("display_b", RUN_DETAIL / "_imports_display_b.py"),
        ],
    )


if __name__ == "__main__":
    main()
