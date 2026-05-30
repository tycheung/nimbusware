#!/usr/bin/env python3
"""Split test_console_bundle_catalog.py into search / faiss / catalog modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tests/console/test_console_bundle_catalog.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

HEADER_END = 136  # through imports and pytestmark
HEADER = "".join(lines[:HEADER_END])

MODULES = [
    ("test_console_bundle_search.py", 137, 321),
    ("test_console_bundle_faiss.py", 322, 1225),
    ("test_console_bundle_catalog_rollup.py", 1226, len(lines)),
]

for name, start, end in MODULES:
    body = "".join(lines[start - 1 : end])
    (ROOT / "tests/console" / name).write_text(HEADER + body, encoding="utf-8")
    print(f"wrote {name} ({end - start + 1} test lines)")

SRC.unlink()
print("removed test_console_bundle_catalog.py")
