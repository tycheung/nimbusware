#!/usr/bin/env python3
"""Remove obvious redundant comment-only lines from Python sources."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (ROOT / "packages", ROOT / "scripts")
SKIP_PARTS = {".venv", "node_modules", "__pycache__", "dist", "build"}

REDUNDANT_PATTERNS = (
    re.compile(r"^\s*#\s*Cross-platform:.*$"),
    re.compile(r"^\s*#\s*Built by scripts/publish/.*$"),
    re.compile(r"^\s*#\s*Output: dist/.*$"),
    re.compile(r"^\s*#\s*Work files:.*$"),
    re.compile(r"^\s*#\s*Spec:.*$"),
    re.compile(r"^\s*#\s*Place the exe.*$"),
    re.compile(r"^\s*#\s*fmt: off\s*$"),
    re.compile(r"^\s*#\s*fmt: on\s*$"),
    re.compile(r"^\s*#\s*noqa:\s*[A-Z]+\d+\s*-\s*.*$"),
    re.compile(r"^\s*#\s*type: ignore\[.*\]\s*-\s*.*$"),
    re.compile(r"^\s*#\s*Intentionally (empty|silent).*$"),
    re.compile(r'^\s*"""\s*Re-export.*\.\s*"""\s*$'),
    re.compile(r'^\s*"""\s*Thin wrapper.*\.\s*"""\s*$'),
)


def should_scan(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in SKIP_PARTS for part in path.parts)


def prune_file(path: Path, *, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept: list[str] = []
    changed = False
    for line in lines:
        if any(pattern.match(line) for pattern in REDUNDANT_PATTERNS):
            changed = True
            continue
        kept.append(line)
    if not changed:
        return False
    new_text = "\n".join(kept)
    if text.endswith("\n"):
        new_text += "\n"
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prune redundant comment lines")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    changed = 0
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if not should_scan(path):
                continue
            if prune_file(path, dry_run=args.dry_run):
                changed += 1
                print(path.relative_to(ROOT))
    print(f"pruned {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
