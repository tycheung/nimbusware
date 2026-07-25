#!/usr/bin/env python3




from __future__ import annotations



import ast

import os

import sys

from collections import defaultdict

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]



# (package dir under packages/, forbidden import substring)
# Product modules cleared via facades (sak408-c/d, sak409-b–d); gate retained as guardrail.

FORBIDDEN_EDGES: tuple[tuple[str, str], ...] = (

    ("agent_tools", "orchestrator.llm"),

    ("research", "orchestrator.registry"),

)





def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
        and path.is_file()
        and not path.name.endswith("_facade.py")
        and "facades" not in path.parts
    )





def _import_strings(path: Path) -> list[str]:

    tree = ast.parse(path.read_text(encoding="utf-8"))

    hits: list[str] = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            hits.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                hits.append(node.module)

    return hits





def forbidden_hits(root: Path | None = None) -> list[str]:

    repo_root = root or ROOT

    packages = repo_root / "packages"

    violations: list[str] = []

    for package_dir, forbidden in FORBIDDEN_EDGES:

        scan_root = packages / package_dir

        if not scan_root.is_dir():

            continue

        for path in _iter_python_files(scan_root):

            imports = _import_strings(path)

            for imp in imports:

                if forbidden in imp:

                    rel = path.relative_to(repo_root)

                    violations.append(f"{rel.as_posix()}: {imp} (forbidden edge -> {forbidden})")

    return violations





def forbidden_hits_by_package(root: Path | None = None) -> dict[str, list[str]]:

    grouped: dict[str, list[str]] = defaultdict(list)

    for item in forbidden_hits(root):

        rel = item.split(":", 1)[0]

        package = rel.split("/", 2)[1] if rel.startswith("packages/") else "unknown"

        grouped[package].append(item)

    return dict(grouped)





def _emit_hits(hits: list[str], by_pkg: dict[str, list[str]], *, strict: bool) -> None:
    label = "error" if strict else "warn"
    stream = sys.stderr if strict else sys.stdout
    print(f"peel import graph {label}: {len(hits)} forbidden edge(s)", file=stream)
    for package in sorted(by_pkg):
        pkg_hits = by_pkg[package]
        print(f"  {package}: {len(pkg_hits)} hit(s)", file=stream)
        for item in pkg_hits:
            print(f"    {item}", file=stream)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repo root containing packages/ (for tests)",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even when forbidden edges are found (default: strict fail)",
    )
    args = parser.parse_args(argv)

    hits = forbidden_hits(args.root)
    by_pkg = forbidden_hits_by_package(args.root)
    strict = not args.warn_only and os.environ.get("NIMBUSWARE_PEEL_STRICT", "1") != "0"

    if hits:
        _emit_hits(hits, by_pkg, strict=strict)
        return 1 if strict else 0

    print("peel import graph: ok")
    return 0





if __name__ == "__main__":

    raise SystemExit(main())


