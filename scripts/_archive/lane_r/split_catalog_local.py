"""Mechanical split of bundle_catalog/catalog_local.py into catalog_local/."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/bundle_catalog/catalog_local.py"
OUT = REPO / "packages/nimbusware_console/bundle_catalog/catalog_local"

COMMON_IMPORTS = '''from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

'''

MODULES: dict[str, tuple[int, int, str, str]] = {
    "_constants.py": (
        15,
        18,
        '"""Local bundle catalog constants."""',
        "",
    ),
    "_cells.py": (
        73,
        78,
        '"""Shared cell formatters for local catalog exports."""',
        "",
    ),
    "summary.py": (
        20,
        246,
        '"""Local bundle catalog summary and operator metrics."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS,\n"
        "    _bundle_catalog_local_summary_cell,\n"
        ")\n"
        "from nimbusware_console.bundle_catalog.catalog_local._constants import (\n"
        "    _LOCAL_CATALOG_RELPATH,\n"
        ")\n",
    ),
    "tags.py": (
        248,
        515,
        '"""Local bundle catalog tag samples, counts, and captions."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _bundle_search_hit_cell,\n"
        ")\n"
        "from nimbusware_console.bundle_catalog.catalog_local.rollup_without_tags import (\n"
        "    bundle_catalog_bundles_without_tags_count,\n"
        ")\n"
        "from nimbusware_console.bundle_catalog.catalog_local.summary import (\n"
        "    bundle_catalog_local_summary,\n"
        ")\n",
    ),
    "rollup_without_tags.py": (
        517,
        761,
        '"""Rollup helpers for bundles without tags."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS,\n"
        "    _bundle_catalog_local_summary_cell,\n"
        ")\n"
        "from nimbusware_console.bundle_catalog.catalog_local.summary import (\n"
        "    bundle_catalog_local_summary,\n"
        ")\n",
    ),
    "rollup_without_id.py": (
        763,
        988,
        '"""Rollup helpers for bundles without id."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,\n"
        "    _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS,\n"
        "    _bundle_catalog_local_summary_cell,\n"
        ")\n"
        "from nimbusware_console.bundle_catalog.catalog_local.summary import (\n"
        "    bundle_catalog_local_summary,\n"
        ")\n",
    ),
    "faiss_helpers.py": (
        990,
        1141,
        '"""FAISS sync helper internals shared with faiss_status."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _mtime_iso_utc_ns,\n"
        ")\n",
    ),
    "search.py": (
        1143,
        1584,
        '"""Bundle catalog search captions, metrics, and local search runner."""',
        "from nimbusware_console.bundle_catalog.catalog_local._cells import (\n"
        "    _bundle_search_hit_cell,\n"
        ")\n",
    ),
}


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def _write_cells_module(lines: list[str]) -> None:
    parts = [
        _slice_lines(lines, 70, 78),
        "\n",
        _slice_lines(lines, 131, 134),
        "\n",
        _slice_lines(lines, 1000, 1017),
        "\n",
        _slice_lines(lines, 1526, 1537),
    ]
    text = (
        '"""Shared cell formatters for local catalog exports."""\n\n'
        + COMMON_IMPORTS
        + "".join(parts)
    )
    (OUT / "_cells.py").write_text(text, encoding="utf-8")


def _write_constants_module(lines: list[str]) -> None:
    text = (
        '"""Local bundle catalog constants."""\n\n'
        + COMMON_IMPORTS
        + _slice_lines(lines, 15, 18)
    )
    (OUT / "_constants.py").write_text(text, encoding="utf-8")


def _write_module(name: str, body: str, doc: str, extra_imports: str) -> None:
    text = f"{doc}\n\n{COMMON_IMPORTS}{extra_imports}\n{body}"
    if not text.endswith("\n"):
        text += "\n"
    (OUT / name).write_text(text, encoding="utf-8")


def _write_init() -> None:
    init = '''"""Local bundle catalog summaries, tags, rollups, and search — facade."""

from nimbusware_console.bundle_catalog.catalog_local._cells import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local._constants import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.faiss_helpers import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.rollup_without_id import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.rollup_without_tags import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.search import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.summary import *  # noqa: F403
from nimbusware_console.bundle_catalog.catalog_local.tags import *  # noqa: F403
'''
    (OUT / "__init__.py").write_text(init, encoding="utf-8")


def _summary_body(lines: list[str]) -> str:
    return (
        _slice_lines(lines, 20, 69)
        + _slice_lines(lines, 81, 130)
        + _slice_lines(lines, 137, 246)
    )


def _faiss_helpers_body(lines: list[str]) -> str:
    return _slice_lines(lines, 990, 999) + _slice_lines(lines, 1020, 1141)


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    _write_constants_module(lines)
    _write_cells_module(lines)

    for name, (start, end, doc, extra_imports) in MODULES.items():
        if name in {"_constants.py", "_cells.py"}:
            continue
        if name == "faiss_helpers.py":
            body = _faiss_helpers_body(lines)
        elif name == "summary.py":
            body = _summary_body(lines)
        else:
            body = _slice_lines(lines, start, end)
        _write_module(name, body, doc, extra_imports)

    _write_init()

    export_fn = OUT / "search.py"
    export_text = export_fn.read_text(encoding="utf-8")
    export_text = export_text.replace(
        "    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)",
        "    from nimbusware_console.bundle_catalog.faiss_status import (\n"
        "        bundle_faiss_operator_drilldown_export_filename_slug,\n"
        "    )\n\n"
        "    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)",
    )
    export_fn.write_text(export_text, encoding="utf-8")

    SRC.unlink()
    print(f"Split {SRC} -> {OUT}/ ({len(MODULES)} modules)")


if __name__ == "__main__":
    main()
