#!/usr/bin/env python3
"""Split run_detail/_imports.py on complete import blocks."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "packages/nimbusware_console/pages/run_detail/_imports.py"
PKG = ROOT / "packages/nimbusware_console/pages/run_detail"

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

# Header through streamlit import (skip original module docstring)
future_idx = next(i for i, ln in enumerate(lines) if ln.startswith("from __future__"))
common_end = next(i for i, ln in enumerate(lines) if ln.startswith("import streamlit"))
COMMON = "".join(lines[future_idx : common_end + 1])

# Tail from settings import
settings_start = next(i for i, ln in enumerate(lines) if ln.startswith("from nimbusware_console.settings"))
TAIL = "".join(lines[settings_start:])

# Parse import blocks between common and tail
middle = lines[common_end + 1 : settings_start]
blocks: list[str] = []
buf: list[str] = []
for ln in middle:
    if ln.strip() == "" and not buf:
        continue
    buf.append(ln)
    if ln.rstrip().endswith(")"):
        blocks.append("".join(buf).strip() + "\n\n")
        buf = []
if buf:
    raise RuntimeError("unfinished import block at end of middle section")

mid = len(blocks) // 2
blocks_a = blocks[:mid]
blocks_b = blocks[mid:]

HEADER = '"""Shared imports for run_detail section modules (part {part})."""\n\nfrom __future__ import annotations\n\n'

(PKG / "_imports_common.py").write_text(
    '"""Stdlib and framework imports for run_detail panels."""\n\n' + COMMON,
    encoding="utf-8",
)
(PKG / "_imports_display_a.py").write_text(HEADER.format(part="A") + "".join(blocks_a), encoding="utf-8")
(PKG / "_imports_display_b.py").write_text(HEADER.format(part="B") + "".join(blocks_b), encoding="utf-8")

shim = '''"""Shared imports for run_detail section modules."""

from __future__ import annotations

from nimbusware_console.pages.run_detail._imports_common import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_a import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_display_b import *  # noqa: F403
''' + TAIL

SRC.write_text(shim, encoding="utf-8")
print(
    f"split _imports.py -> common + display_a ({len(blocks_a)} blocks) "
    f"+ display_b ({len(blocks_b)} blocks)",
)
