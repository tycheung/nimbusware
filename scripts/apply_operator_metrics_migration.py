"""Replace duplicated field/value export helpers with operator_metrics."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

IMPORT_BLOCK = (
    "from nimbusware_console.components.operator_metrics import (\n"
    "    FIELD_VALUE_COLUMNS,\n"
    "    field_value_table_rows_csv,\n"
    "    mapping_export_json,\n"
    "    mapping_to_sorted_table_rows,\n"
    "    sequence_export_json,\n"
    "    table_rows_csv,\n"
    ")\n"
)

TARGETS = [
    REPO / "packages/nimbusware_console/bundle_catalog/faiss_status.py",
    REPO / "packages/nimbusware_console/integrator_gate_display.py",
    REPO / "packages/nimbusware_console/persona_catalog.py",
    REPO / "packages/nimbusware_console/agent_evaluator_workflow_explainer.py",
    REPO / "packages/nimbusware_console/escalation_suppress_workflow_explainer.py",
    REPO / "packages/nimbusware_console/integrator_threshold_explainer.py",
    REPO / "packages/nimbusware_console/integrator_workflow_preview.py",
    REPO / "packages/nimbusware_console/security_scan_metadata_workflow_explainer.py",
    REPO / "packages/nimbusware_console/self_refinement_workflow_explainer.py",
    REPO / "packages/nimbusware_console/universal_critique_workflow_explainer.py",
]

FIELD_VALUE_CONST = re.compile(
    r"^_[A-Z0-9_]+(?:CSV_COLUMNS|_CSV_COLUMNS): tuple\[str, \.\.\.\] = \(\n"
    r'    "field",\n'
    r'    "value",\n'
    r"\)\n\n",
    re.MULTILINE,
)

FIELD_VALUE_CONST_SINGLE = re.compile(
    r'^_[A-Z0-9_]+(?:CSV_COLUMNS|_CSV_COLUMNS): tuple\[str, \.\.\.\] = \("field", "value"\)\n\n',
    re.MULTILINE,
)

CSV_FUNC = re.compile(
    r"def (?P<name>[a-z_0-9]+_table_rows_csv)\(\n"
    r"    rows: Sequence\[Mapping\[str, str\]\],\n"
    r"\) -> str:\n"
    r"    if not rows:\n"
    r'        return ""\n'
    r"    buf = StringIO\(\)\n"
    r"    w = csv\.DictWriter\(\n"
    r"        buf,\n"
    r"        fieldnames=list\(_[A-Z0-9_]+\),\n"
    r'        extrasaction="ignore",\n'
    r"    \)\n"
    r"    w\.writeheader\(\)\n"
    r"    for r in rows:\n"
    r"        if isinstance\(r, Mapping\):\n"
    r"            w\.writerow\(\n"
    r"                \{k: r\.get\(k, \"\"\) for k in _[A-Z0-9_]+\},\n"
    r"            \)\n"
    r"    return buf\.getvalue\(\)\n",
    re.MULTILINE,
)

CSV_FUNC_ALT = re.compile(
    r"def (?P<name>[a-z_0-9]+_table_rows_csv)\(\n"
    r"    rows: Sequence\[Mapping\[str, str\]\],\n"
    r"\) -> str:\n"
    r"    if not rows:\n"
    r'        return ""\n'
    r"    buf = StringIO\(\)\n"
    r"    w = csv\.DictWriter\(\n"
    r"        buf,\n"
    r"        fieldnames=list\(_[A-Z0-9_]+\),\n"
    r'        extrasaction="ignore",\n'
    r"    \)\n"
    r"    w\.writeheader\(\)\n"
    r"    for r in rows:\n"
    r"        if isinstance\(r, Mapping\):\n"
    r"            w\.writerow\(\{k: r\.get\(k, \"\"\) for k in _[A-Z0-9_]+\}\)\n"
    r"    return buf\.getvalue\(\)\n",
    re.MULTILINE,
)

METRICS_CSV_FUNC = re.compile(
    r"def (?P<name>[a-z_0-9]+_operator_metrics_table_rows_csv)\(\n"
    r"    rows: Sequence\[Mapping\[str, str\]\],\n"
    r"\) -> str:\n"
    r"    if not rows:\n"
    r'        return ""\n'
    r"    buf = StringIO\(\)\n"
    r"    w = csv\.DictWriter\(\n"
    r"        buf,\n"
    r"        fieldnames=list\(_[A-Z0-9_]+\),\n"
    r'        extrasaction="ignore",\n'
    r"    \)\n"
    r"    w\.writeheader\(\)\n"
    r"    for r in rows:\n"
    r"        if isinstance\(r, Mapping\):\n"
    r"            w\.writerow\(\n"
    r"                \{\n"
    r"                    k: r\.get\(k, \"\"\)\n"
    r"                    for k in _[A-Z0-9_]+\n"
    r"                \},\n"
    r"            \)\n"
    r"    return buf\.getvalue\(\)\n",
    re.MULTILINE,
)

MAPPING_EXPORT = re.compile(
    r"def (?P<name>[a-z_0-9]+_export_json)\(\n"
    r"    (?P<arg>[a-z_]+): Mapping\[str, Any\] \| None,\n"
    r"\) -> str:\n"
    r"    if not isinstance\((?P=arg), Mapping\):\n"
    r'        return "{}"\n'
    r"    return json\.dumps\(dict\((?P=arg)\), indent=2, ensure_ascii=False\)\n",
    re.MULTILINE,
)

METRICS_EXPORT = re.compile(
    r"def (?P<name>[a-z_0-9]+_operator_metrics_export_json)\(\n"
    r"    (?P<arg>[a-z_]+): Mapping\[str, Any\] \| None,\n"
    r"\) -> str:\n"
    r"    if not isinstance\((?P=arg), Mapping\):\n"
    r'        return "{}"\n'
    r"    return json\.dumps\(dict\((?P=arg)\), indent=2, ensure_ascii=False\)\n",
    re.MULTILINE,
)

SORTED_TABLE_ROWS = re.compile(
    r"def (?P<name>[a-z_0-9]+_table_rows)\(\n"
    r"    (?P<arg>[a-z_]+): Mapping\[str, Any\] \| None,\n"
    r"\) -> list\[dict\[str, str\]\]:\n"
    r"    if not isinstance\((?P=arg), Mapping\):\n"
    r"        return \[\]\n"
    r"    rows: list\[dict\[str, str\]\] = \[\]\n"
    r"    for key in sorted\(str\(k\) for k in (?P=arg)\.keys\(\)\):\n"
    r"        rows\.append\(\n"
    r"            \{\n"
    r'                "field": key,\n'
    r'                "value": (?P<cell>_[a-z_]+\((?P=arg)\.get\(key\)\)),\n'
    r"            \},\n"
    r"        \)\n"
    r"    return rows\n",
    re.MULTILINE,
)


def _ensure_import(text: str) -> str:
    if "nimbusware_console.components.operator_metrics" in text:
        return text
    marker = "from __future__ import annotations\n\n"
    if marker not in text:
        return IMPORT_BLOCK + text
    return text.replace(marker, marker + IMPORT_BLOCK, 1)


def _replace_csv(text: str, pattern: re.Pattern[str], label: str) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        return f"def {name}(\n    rows: Sequence[Mapping[str, str]],\n) -> str:\n    return field_value_table_rows_csv(rows)\n"

    new, n = pattern.subn(repl, text)
    if n:
        print(f"  {label}: {n} csv helpers")
    return new


def _replace_export(text: str, pattern: re.Pattern[str], label: str) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        arg = match.group("arg")
        return (
            f"def {name}(\n    {arg}: Mapping[str, Any] | None,\n) -> str:\n"
            f"    return mapping_export_json({arg})\n"
        )

    new, n = pattern.subn(repl, text)
    if n:
        print(f"  {label}: {n} export_json helpers")
    return new


def _replace_sorted_rows(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group("name")
        arg = match.group("arg")
        cell = match.group("cell")
        return (
            f"def {name}(\n    {arg}: Mapping[str, Any] | None,\n) -> list[dict[str, str]]:\n"
            f"    return mapping_to_sorted_table_rows({arg}, {cell.split('(')[0]})\n"
        )

    new, n = SORTED_TABLE_ROWS.subn(repl, text)
    if n:
        print(f"  sorted table rows: {n}")
    return new


def _strip_field_value_constants(text: str) -> str:
    text = FIELD_VALUE_CONST.sub("", text)
    text = FIELD_VALUE_CONST_SINGLE.sub("", text)
    return text


def _maybe_drop_csv_imports(text: str) -> str:
    if "csv." in text or "StringIO(" in text or "DictWriter" in text:
        return text
    text = re.sub(r"^import csv\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^from io import StringIO\n", "", text, flags=re.MULTILINE)
    return text


def migrate_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    text = original
    text = _replace_csv(text, CSV_FUNC, "csv")
    text = _replace_csv(text, CSV_FUNC_ALT, "csv-alt")
    text = _replace_csv(text, METRICS_CSV_FUNC, "metrics-csv")
    text = _replace_export(text, MAPPING_EXPORT, "export")
    text = _replace_export(text, METRICS_EXPORT, "metrics-export")
    text = _replace_sorted_rows(text)
    text = _strip_field_value_constants(text)
    if text != original:
        text = _ensure_import(text)
        text = _maybe_drop_csv_imports(text)
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(REPO))


def main() -> None:
    for path in TARGETS:
        if path.is_file():
            migrate_file(path)
        else:
            print(f"skip missing {path}")


if __name__ == "__main__":
    main()
