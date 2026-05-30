"""Mechanical split of integrator_gate_display.py into integrator_gate/ package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/integrator_gate_display.py"
OUT = REPO / "packages/nimbusware_console/integrator_gate"

HEADER = '''from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    table_rows_csv,
)
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

'''

MODULES: dict[str, tuple[int, int]] = {
    "_helpers.py": (1, 63),
    "history.py": (66, 364),
    "latest_delta.py": (365, 9999),
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
        if name == "history.py":
            extra = (
                "from nimbusware_console.integrator_gate._helpers import (\n"
                "    _format_tag_list_sample,\n"
                "    _stringify,\n"
                ")\n"
            )
        if name == "latest_delta.py":
            extra = (
                "from nimbusware_console.integrator_gate._helpers import (\n"
                "    _optional_float,\n"
                "    _stringify,\n"
                "    integrator_gate_from_timeline,\n"
                "    integrator_gate_history_from_timeline,\n"
                ")\n"
                "from nimbusware_console.integrator_gate.history import (\n"
                "    integrator_gate_history_operator_metrics,\n"
                ")\n"
            )
        if name == "_helpers.py":
            text = HEADER + body.split("from __future__ import annotations\n\n", 1)[-1]
        else:
            text = HEADER + extra + body
        if not text.endswith("\n"):
            text += "\n"
        (OUT / name).write_text(text, encoding="utf-8")

    init = """from nimbusware_console.integrator_gate._helpers import *  # noqa: F403
from nimbusware_console.integrator_gate.history import *  # noqa: F403
from nimbusware_console.integrator_gate.latest_delta import *  # noqa: F403
"""
    (OUT / "__init__.py").write_text(init, encoding="utf-8")

    facade = SRC.parent / "integrator_gate_display.py"
    facade.write_text(
        "from nimbusware_console.integrator_gate import *  # noqa: F403\n",
        encoding="utf-8",
    )
    SRC.unlink()
    print(f"Split integrator_gate_display -> {OUT}/")


if __name__ == "__main__":
    main()
