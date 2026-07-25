#!/usr/bin/env python3




from __future__ import annotations



import argparse

import ast

import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

_PACKAGES = ("agent_tools", "research")

_ORCHESTRATOR_PREFIX = "orchestrator"





def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
        and path.is_file()
        and not path.name.endswith("_facade.py")
        and "facades" not in path.parts
    )





def _orchestrator_imports(path: Path) -> list[str]:

    tree = ast.parse(path.read_text(encoding="utf-8"))

    hits: list[str] = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                if alias.name == _ORCHESTRATOR_PREFIX or alias.name.startswith(

                    f"{_ORCHESTRATOR_PREFIX}."

                ):

                    hits.append(alias.name)

        elif isinstance(node, ast.ImportFrom):

            mod = node.module or ""

            if mod == _ORCHESTRATOR_PREFIX or mod.startswith(f"{_ORCHESTRATOR_PREFIX}."):

                hits.append(mod)

    return hits





def collect_reverse_imports(

    package: str,

    *,

    root: Path | None = None,

) -> list[tuple[str, list[str]]]:

    repo_root = root or ROOT

    package_root = repo_root / "packages" / package

    findings: list[tuple[str, list[str]]] = []

    for path in _iter_python_files(package_root):

        hits = _orchestrator_imports(path)

        if hits:

            rel = path.relative_to(repo_root / "packages")

            findings.append((rel.as_posix(), sorted(set(hits))))

    return findings





def collect_all_packages(

    packages: tuple[str, ...] = _PACKAGES,

    *,

    root: Path | None = None,

) -> dict[str, list[tuple[str, list[str]]]]:

    return {pkg: collect_reverse_imports(pkg, root=root) for pkg in packages}





def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(

        "--package",

        choices=_PACKAGES,

        action="append",

        dest="packages",

        help="Scan only this package (default: agent_tools and research)",

    )

    args = parser.parse_args(argv)

    selected = tuple(args.packages) if args.packages else _PACKAGES



    for package in selected:

        findings = collect_reverse_imports(package)

        print(f"{package}->orchestrator import sites: {len(findings)}")

        for rel, mods in findings:

            print(f"  {rel}: {mods}")

    return 0





if __name__ == "__main__":

    raise SystemExit(main())


