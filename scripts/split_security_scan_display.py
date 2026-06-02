from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "packages/nimbusware_console/security_scan_on_verify_display.py"
text = src.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

# 1-based split boundaries (inclusive start, exclusive end for slices).
SLICES: tuple[tuple[str, int, int], ...] = (
    ("_helpers.py", 1, 33),
    ("timeline.py", 34, 291),
    ("history_metrics.py", 292, 393),
    ("linter.py", 394, 626),
    ("latest.py", 627, 856),
    ("alignment.py", 857, 9999),
)

IMPORTS: dict[str, str] = {
    "_helpers.py": "",
    "timeline.py": (
        "import csv\nimport json\nimport re\n"
        "from collections.abc import Mapping, Sequence\n"
        "from io import StringIO\nfrom typing import Any\n\n"
        "from nimbusware_console.security_scan_on_verify._helpers import _stringify\n"
    ),
    "history_metrics.py": (
        "from collections.abc import Mapping\n"
        "from datetime import datetime, timezone\n"
        "from typing import Any\n\n"
        "from nimbusware_console.security_scan_on_verify._helpers import _stringify\n"
    ),
    "linter.py": (
        "from collections.abc import Mapping\nfrom typing import Any\n\n"
        "from nimbusware_console.security_scan_on_verify._helpers import _stringify\n"
    ),
    "latest.py": (
        "import csv\nimport json\nimport re\n"
        "from collections.abc import Mapping, Sequence\n"
        "from io import StringIO\nfrom typing import Any\n\n"
        "from nimbusware_console.security_scan_on_verify._helpers import (\n"
        "    _SECURITY_SCAN_ON_VERIFY_FIELDS,\n"
        "    _stringify,\n"
        ")\n"
    ),
    "alignment.py": (
        "from collections.abc import Mapping\n\n"
        "from nimbusware_console.security_scan_on_verify.latest import (\n"
        "    security_scan_on_verify_summary_rows,\n"
        ")\n"
    ),
}

pkg = ROOT / "packages/nimbusware_console/security_scan_on_verify"
pkg.mkdir(exist_ok=True)

for name, start, end in SLICES:
    chunk = "".join(lines[start - 1 : end - 1])
    header = 'from __future__ import annotations\n\n'
    extra = IMPORTS.get(name, "")
    if name == "_helpers.py":
        body = chunk
    else:
        body = header + extra + "\n" + chunk.lstrip()
    (pkg / name).write_text(body, encoding="utf-8")

init = '''"""Security scan on verify timeline display helpers."""

from nimbusware_console.security_scan_on_verify._helpers import *  # noqa: F403
from nimbusware_console.security_scan_on_verify.timeline import *  # noqa: F403
from nimbusware_console.security_scan_on_verify.history_metrics import *  # noqa: F403
from nimbusware_console.security_scan_on_verify.linter import *  # noqa: F403
from nimbusware_console.security_scan_on_verify.latest import *  # noqa: F403
from nimbusware_console.security_scan_on_verify.alignment import *  # noqa: F403
'''
(pkg / "__init__.py").write_text(init, encoding="utf-8")
src.write_text(
    "from nimbusware_console.security_scan_on_verify import *  # noqa: F403\n",
    encoding="utf-8",
)
print("security_scan split done")
