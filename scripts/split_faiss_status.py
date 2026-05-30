"""Split bundle_catalog/faiss_status.py into faiss_status/ by function boundaries."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/bundle_catalog/faiss_status.py"
OUT = REPO / "packages/nimbusware_console/bundle_catalog/faiss_status"

HEADER = '''from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_faiss_index_status_cell,
    _bundle_faiss_readiness_summary_cell,
)
from nimbusware_console.bundle_catalog.catalog_local.faiss_helpers import (
    _bundle_faiss_mtime_observability,
    _bundle_order_duplicate_id_signals,
    _bundle_order_list_length,
    _catalog_bundle_row_counts,
    _catalog_nonempty_stripped_id_set,
    _file_size_mtime,
    _parse_bundle_order_string_ids,
)

'''

SECTION_STARTS = (
    ("status.py", "bundle_faiss_index_status_operator_metrics"),
    ("readiness.py", "bundle_faiss_readiness_summary"),
    ("index_status.py", "bundle_faiss_index_stale_caption"),
    ("drilldown.py", "bundle_faiss_index_operator_drilldown"),
)


def _def_lines(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^def ([a-z_0-9]+)\(", line)
        if m:
            out[m.group(1)] = i
    return out


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    defs = _def_lines(text)

    const_start = next(
        i for i, line in enumerate(lines, start=1) if line.startswith("BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH")
    )
    const_end = next(
        i for i, line in enumerate(lines, start=1) if line.startswith("def bundle_faiss_index_status_operator_metrics")
    )

    OUT.mkdir(parents=True, exist_ok=True)
    const_body = _slice_lines(lines, const_start, const_end - 1)
    (OUT / "_constants.py").write_text(
        'from __future__ import annotations\n\n' + const_body,
        encoding="utf-8",
    )

    starts = [(name, defs[fn]) for name, fn in SECTION_STARTS]
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] - 1 if idx + 1 < len(starts) else len(lines)
        body = _slice_lines(lines, start, end)
        (OUT / name).write_text(HEADER + body, encoding="utf-8")

    init = """from nimbusware_console.bundle_catalog.faiss_status._constants import *  # noqa: F403
from nimbusware_console.bundle_catalog.faiss_status.drilldown import *  # noqa: F403
from nimbusware_console.bundle_catalog.faiss_status.index_status import *  # noqa: F403
from nimbusware_console.bundle_catalog.faiss_status.readiness import *  # noqa: F403
from nimbusware_console.bundle_catalog.faiss_status.status import *  # noqa: F403
"""
    (OUT / "__init__.py").write_text(init, encoding="utf-8")
    SRC.unlink()
    print(f"Split {SRC.name} -> {OUT}/")


if __name__ == "__main__":
    main()
