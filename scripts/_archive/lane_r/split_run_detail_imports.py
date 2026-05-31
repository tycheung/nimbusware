#!/usr/bin/env python3
"""Convert run_detail/_imports.py into a package with common + display modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "packages/nimbusware_console/pages/run_detail/_imports.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

# Lines 1-16: module doc + stdlib/framework through streamlit
COMMON_END = 16
# From first display import through end (before settings block at end)
SETTINGS_START = next(i for i, ln in enumerate(lines) if ln.startswith("from nimbusware_console.settings"))
DISPLAY_A_END = SETTINGS_START // 2 + COMMON_END // 2  # rough midpoint among display imports

# Better split: find line ~400
mid = 400
common = "".join(lines[:COMMON_END])
display_a = "".join(lines[COMMON_END:mid])
display_b = "".join(lines[mid:SETTINGS_START])
settings_tail = "".join(lines[SETTINGS_START:])

pkg = ROOT / "packages/nimbusware_console/pages/run_detail/_imports_pkg"
pkg.mkdir(exist_ok=True)

(pkg / "common.py").write_text(
    '"""Stdlib and framework imports for run_detail panels."""\n\n' + common,
    encoding="utf-8",
)
(pkg / "display_a.py").write_text(
    '"""Display helpers (part A) for run_detail panels."""\n\nfrom __future__ import annotations\n\n'
    + display_a,
    encoding="utf-8",
)
(pkg / "display_b.py").write_text(
    '"""Display helpers (part B) for run_detail panels."""\n\nfrom __future__ import annotations\n\n'
    + display_b,
    encoding="utf-8",
)

init = '''"""Shared imports for run_detail section modules."""

from __future__ import annotations

from nimbusware_console.pages.run_detail._imports_pkg.common import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_pkg.display_a import *  # noqa: F403
from nimbusware_console.pages.run_detail._imports_pkg.display_b import *  # noqa: F403
''' + settings_tail
(pkg / "__init__.py").write_text(init, encoding="utf-8")

# Replace _imports.py with thin shim to package
SRC.write_text(
    '''"""Backward-compatible import hub for run_detail section modules."""

from nimbusware_console.pages.run_detail._imports_pkg import *  # noqa: F403
''',
    encoding="utf-8",
)
print("split _imports.py into _imports_pkg/")
