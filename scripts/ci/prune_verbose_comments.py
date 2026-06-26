#!/usr/bin/env python3

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
    re.compile(r"^\s*#\s*Backward[- ]compatible.*$"),
    re.compile(r"^\s*#\s*See also:.*$"),
    re.compile(r"^\s*#\s*Deprecated:.*$"),
    re.compile(r"^\s*#\s*Legacy (compat|shim).*$"),
)


def should_scan(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in SKIP_PARTS for part in path.parts)


def _is_trivial_module_docstring(body: list[str]) -> bool:
    text = " ".join(line.strip() for line in body if line.strip())
    if not text or len(text) > 160:
        return False
    lowered = text.lower()
    if any(token in lowered for token in ("must", "warning", "deprecated", "security", "invariant")):
        return False
    return True


def prune_file(path: Path, *, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept: list[str] = []
    changed = False
    idx = 0
    if lines and lines[0].startswith("from __future__"):
        kept.append(lines[0])
        idx = 1
        while idx < len(lines) and not lines[idx].strip():
            kept.append(lines[idx])
            idx += 1
    if idx < len(lines) and lines[idx].strip() == '"""':
        doc_lines: list[str] = []
        j = idx + 1
        while j < len(lines) and lines[j].strip() != '"""':
            doc_lines.append(lines[j])
            j += 1
        if j < len(lines) and _is_trivial_module_docstring(doc_lines):
            changed = True
            idx = j + 1
            while idx < len(lines) and not lines[idx].strip():
                idx += 1
    for line in lines[idx:]:
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
