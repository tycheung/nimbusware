"""Split self_refinement_display.py into a package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "packages/nimbusware_console/self_refinement_display.py"
text = src.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

SLICES: tuple[tuple[str, int, int], ...] = (
    ("_helpers.py", 1, 53),
    ("marker_history.py", 54, 265),
    ("captions.py", 266, 525),
    ("latest.py", 526, 612),
    ("timeline_metrics.py", 613, 9999),
)

IMPORTS: dict[str, str] = {
    "_helpers.py": "",
    "marker_history.py": (
        "import csv\nimport json\nimport re\n"
        "from collections.abc import Mapping, Sequence\n"
        "from io import StringIO\nfrom typing import Any\n\n"
        "from nimbusware_console.self_refinement._helpers import _stringify\n"
    ),
    "captions.py": (
        "from collections.abc import Mapping\n"
        "from datetime import datetime, timezone\n"
        "from typing import Any\n\n"
        "from nimbusware_console.self_refinement._helpers import _stringify\n"
    ),
    "latest.py": (
        "import csv\nimport json\nimport re\n"
        "from collections.abc import Mapping, Sequence\n"
        "from io import StringIO\nfrom typing import Any\n\n"
        "from nimbusware_console.self_refinement._helpers import _stringify\n"
    ),
    "timeline_metrics.py": (
        "import csv\nimport json\n"
        "from collections.abc import Mapping, Sequence\n"
        "from datetime import datetime, timezone\n"
        "from io import StringIO\nfrom typing import Any\n\n"
        "from nimbusware_console.self_refinement._helpers import _stringify\n"
    ),
}

pkg = ROOT / "packages/nimbusware_console/self_refinement"
pkg.mkdir(exist_ok=True)

for name, start, end in SLICES:
    chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
    if name == "_helpers.py":
        body = chunk
    else:
        body = "from __future__ import annotations\n\n" + IMPORTS[name] + "\n" + chunk.lstrip()
    (pkg / name).write_text(body, encoding="utf-8")

init = '''"""Self-refinement timeline display helpers."""

from nimbusware_console.self_refinement._helpers import *  # noqa: F403
from nimbusware_console.self_refinement.marker_history import *  # noqa: F403
from nimbusware_console.self_refinement.captions import *  # noqa: F403
from nimbusware_console.self_refinement.latest import *  # noqa: F403
from nimbusware_console.self_refinement.timeline_metrics import *  # noqa: F403
'''
(pkg / "__init__.py").write_text(init, encoding="utf-8")
src.write_text(
    "from nimbusware_console.self_refinement import *  # noqa: F403\n",
    encoding="utf-8",
)
print("self_refinement split done")
