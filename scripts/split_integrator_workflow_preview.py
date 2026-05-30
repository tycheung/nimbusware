"""Mechanical split of integrator_workflow_preview.py into integrator_preview/ package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/integrator_workflow_preview.py"
OUT = REPO / "packages/nimbusware_console/integrator_preview"

HEADER = '''from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from hermes_extensions.personas import ALLOWED_SHELVES
from hermes_extensions.phase2 import ModuleIntegrator
from hermes_orchestrator.integrator_gate import (
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)

'''

MODULES: dict[str, tuple[int, int]] = {
    "parse.py": (33, 231),
    "merge.py": (232, 813),
    "preview.py": (814, 932),
    "exports.py": (933, 9999),
}


def _slice(lines: list[str], start: int, end: int) -> str:
    end = min(end, len(lines))
    return "".join(lines[start - 1 : end])


def main() -> None:
    original = SRC.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    constants = _slice(lines, 33, 49)

    OUT.mkdir(parents=True, exist_ok=True)

    for name, (start, end) in MODULES.items():
        body = _slice(lines, start, end)
        extra = ""
        if name == "merge.py":
            extra = (
                "from nimbusware_console.integrator_preview.parse import (\n"
                "    ALLOWED_FULL_WORKFLOW_ROOT_KEYS,\n"
                "    _FULL_WORKFLOW_MAPPING_KEYS,\n"
                ")\n"
            )
        if name == "preview.py":
            extra = (
                "from nimbusware_console.integrator_preview.merge import (\n"
                "    full_workflow_merge_diff,\n"
                "    validate_full_workflow_document,\n"
                ")\n"
                "from nimbusware_console.integrator_preview.parse import (\n"
                "    parse_integrator_gate_yaml_fragment,\n"
                "    validate_integrator_gate_block,\n"
                ")\n"
            )
        if name == "exports.py":
            extra = (
                "from nimbusware_console.integrator_preview.merge import (\n"
                "    full_workflow_merge_attention_operator_metrics,\n"
                "    full_workflow_merge_attention_operator_metrics_caption,\n"
                "    full_workflow_merge_attention_operator_metrics_table_rows,\n"
                "    full_workflow_merge_attention_rows,\n"
                "    full_workflow_merge_diff,\n"
                "    full_workflow_merge_diff_operator_metrics,\n"
                "    full_workflow_merge_diff_operator_metrics_caption,\n"
                "    full_workflow_merge_diff_operator_metrics_table_rows,\n"
                "    full_workflow_merge_diff_table_rows,\n"
                ")\n"
            )
        if name == "parse.py":
            text = HEADER + constants + body
        else:
            text = HEADER + extra + body
        if not text.endswith("\n"):
            text += "\n"
        (OUT / name).write_text(text, encoding="utf-8")

    init = """from nimbusware_console.integrator_preview.exports import *  # noqa: F403
from nimbusware_console.integrator_preview.merge import *  # noqa: F403
from nimbusware_console.integrator_preview.parse import *  # noqa: F403
from nimbusware_console.integrator_preview.preview import *  # noqa: F403
"""
    (OUT / "__init__.py").write_text(init, encoding="utf-8")

    facade = SRC.parent / "integrator_workflow_preview.py"
    facade.write_text(
        "from nimbusware_console.integrator_preview import *  # noqa: F403\n",
        encoding="utf-8",
    )
    SRC.unlink()
    print(f"Split integrator_workflow_preview -> {OUT}/")


if __name__ == "__main__":
    main()
