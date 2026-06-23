#!/usr/bin/env python3
"""Sync workflow explainer package __init__.py export install blocks from registry (C50)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONSOLE = REPO / "packages" / "nimbusware_console"

from nimbusware_console.explainer_core.workflow_explainer_registry import (  # noqa: E402
    CODEGEN_BLOCK_END,
    CODEGEN_BLOCK_START,
    WORKFLOW_EXPLAINER_SPECS,
    codegen_install_block,
)

_LEGACY_BLOCK_RE = re.compile(
    r"(?:from nimbusware_console\.explainer_core\.workflow_exports import \(\n"
    r"    install_named_workflow_explainer_exports,\n"
    r"\)\n\n?)?"
    r"install_named_workflow_explainer_exports\(\n"
    r"    globals\(\),\n"
    r'    "[^"]+",\n'
    r"(?:    cell_alias=[^\n]+\n)?"
    r"\)\n?",
    re.MULTILINE,
)

_REGISTRY_IMPORT = (
    "from nimbusware_console.explainer_core.workflow_explainer_registry import (\n"
    "    install_package_workflow_explainer_exports,\n"
    ")\n"
)

_BLOCK_RE = re.compile(
    rf"{re.escape(CODEGEN_BLOCK_START)}.*?{re.escape(CODEGEN_BLOCK_END)}\n?",
    re.DOTALL,
)


def _insert_registry_import(text: str) -> str:
    if "workflow_explainer_registry" in text:
        return text
    match = re.search(
        r"(^from nimbusware_console\.explainer_core\.workflow_exports import[^\n]*\n"
        r"(?:    [^\n]+\n)*\))",
        text,
        re.MULTILINE,
    )
    if match:
        return text[: match.end()] + "\n\n" + _REGISTRY_IMPORT + text[match.end() :]
    lines = text.splitlines(keepends=True)
    insert_at = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("from ") or line.startswith("import "):
            insert_at = i + 1
            if "(" in line and ")" not in line:
                i += 1
                while i < len(lines) and ")" not in lines[i]:
                    i += 1
                insert_at = i + 1
        i += 1
    lines.insert(insert_at, "\n" + _REGISTRY_IMPORT)
    return "".join(lines)


def sync_package_init(spec_package: str, slug: str, *, dry_run: bool = False) -> bool:
    init_path = CONSOLE / spec_package / "__init__.py"
    if not init_path.is_file():
        print(f"missing {init_path.relative_to(REPO)}")
        return False
    block = codegen_install_block(slug)
    text = init_path.read_text(encoding="utf-8")
    new_text = _LEGACY_BLOCK_RE.sub("", text)
    new_text = _BLOCK_RE.sub("", new_text)
    new_text = _insert_registry_import(new_text)
    if CODEGEN_BLOCK_START not in new_text:
        new_text = new_text.rstrip() + "\n\n" + block
    if new_text == text:
        return False
    if dry_run:
        print(f"would sync {init_path.relative_to(REPO)}")
    else:
        init_path.write_text(new_text, encoding="utf-8")
        print(f"synced {init_path.relative_to(REPO)}")
    return True


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    check = "--check" in argv
    changed = 0
    for spec in WORKFLOW_EXPLAINER_SPECS:
        if sync_package_init(spec.package, spec.slug, dry_run=dry_run or check):
            changed += 1
    if check and changed:
        print(f"workflow explainer init drift: {changed} package(s) out of sync")
        return 1
    print(f"{'would sync' if dry_run else 'synced'} {changed} workflow explainer package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
