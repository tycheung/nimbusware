"""Mechanical split of persona_catalog.py into persona_catalog/ package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/persona_catalog.py"
OUT = REPO / "packages/nimbusware_console/persona_catalog"

HEADER = '''from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

'''

MODULES: dict[str, tuple[int, int]] = {
    "load.py": (20, 44),
    "summary.py": (45, 572),
    "pairings.py": (573, 922),
    "export.py": (923, 9999),
}


def _slice(lines: list[str], start: int, end: int) -> str:
    end = min(end, len(lines))
    return "".join(lines[start - 1 : end])


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for name, (start, end) in MODULES.items():
        body = _slice(lines, start, end)
        extra = ""
        if name == "pairings.py":
            extra = "from nimbusware_console.persona_catalog.summary import (\n    _persona_operator_summary_cell,\n)\n"
        if name == "export.py":
            extra = (
                "from nimbusware_console.persona_catalog.load import (\n"
                "    load_persona_shelves_catalog,\n"
                "    persona_catalog_flat_rows,\n"
                ")\n"
            )
        text = HEADER + extra + body
        if not text.endswith("\n"):
            text += "\n"
        (OUT / name).write_text(text, encoding="utf-8")

    init = """from nimbusware_console.persona_catalog.export import *  # noqa: F403
from nimbusware_console.persona_catalog.load import *  # noqa: F403
from nimbusware_console.persona_catalog.pairings import *  # noqa: F403
from nimbusware_console.persona_catalog.summary import *  # noqa: F403
"""
    (OUT / "__init__.py").write_text(init, encoding="utf-8")

    facade = SRC.parent / "persona_catalog.py"
    facade.write_text(
        "from nimbusware_console.persona_catalog import *  # noqa: F403\n",
        encoding="utf-8",
    )
    SRC.unlink()
    print(f"Split persona_catalog -> {OUT}/")


if __name__ == "__main__":
    main()
