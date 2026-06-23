from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    table_rows_csv,
)


def critique_pairings_operator_summary(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    from nimbusware_console.persona_catalog._pairings_load import (
        _CRITIQUE_PAIRINGS_RELPATH,
        critique_pairings_yaml_path,
        load_critique_pairings_doc,
    )

    path = critique_pairings_yaml_path(repo_root)
    doc = load_critique_pairings_doc(repo_root, config_materializer=config_materializer)
    has = doc is not None or path.is_file()
    out: dict[str, Any] = {
        "has_critique_pairings_yaml": has,
        "critique_pairings_yaml_relpath": _CRITIQUE_PAIRINGS_RELPATH if has else None,
        "version": None,
        "producer_taxonomy_key_count": 0,
        "producer_taxonomy_keys": [],
        "producer_taxonomy_keys_sample": [],
        "critique_pairing_critic_role_entries_total": 0,
        "critique_pairing_critic_counts_by_producer": [],
        "critique_pairing_critic_counts_by_producer_sample": [],
        "load_error": None,
    }
    if doc is None:
        if path.is_file():
            out["load_error"] = "critique pairings load failed"
        return out
    ver = doc.get("version")
    if type(ver) is int:
        out["version"] = ver
    elif isinstance(ver, str) and ver.strip():
        out["version"] = ver.strip()
    raw_p = doc.get("pairings")
    if not isinstance(raw_p, dict):
        out["load_error"] = "pairings is not a mapping"
        return out
    excluded_producers = {"agent_evaluator"}
    keys = sorted(str(k) for k in raw_p if isinstance(k, str) and str(k) not in excluded_producers)
    out["producer_taxonomy_key_count"] = len(keys)
    out["producer_taxonomy_keys"] = keys
    out["producer_taxonomy_keys_sample"] = keys[:12]
    total_entries = 0
    per_rows: list[dict[str, str]] = []
    for pk in keys:
        raw_val = raw_p.get(pk)
        if not isinstance(raw_val, list):
            continue
        n = sum(1 for x in raw_val if isinstance(x, str) and str(x).strip())
        total_entries += n
        per_rows.append({"producer": pk, "critic_roles": str(n)})
    out["critique_pairing_critic_role_entries_total"] = total_entries
    out["critique_pairing_critic_counts_by_producer"] = per_rows
    out["critique_pairing_critic_counts_by_producer_sample"] = per_rows[:12]
    return out


def persona_probation_other_examples_by_shelf_table_rows(
    operator_summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    raw = operator_summary.get("probation_status_breakdown_other_examples_by_shelf")
    if not isinstance(raw, dict):
        return []
    out: list[dict[str, str]] = []
    for shelf in sorted(str(k) for k in raw.keys()):
        ex = raw.get(shelf)
        if not isinstance(ex, list) or not ex:
            continue
        usable = [str(x).strip() for x in ex if isinstance(x, str) and str(x).strip()]
        if not usable:
            continue
        out.append(
            {
                "shelf": shelf,
                "other_probation_status_examples": ", ".join(usable),
            },
        )
    return out


_PROBATION_OTHER_BY_SHELF_CSV_COLUMNS: tuple[str, ...] = (
    "shelf",
    "other_probation_status_examples",
)


def persona_probation_other_by_shelf_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


persona_probation_other_by_shelf_table_rows_csv = partial(
    table_rows_csv, columns=_PROBATION_OTHER_BY_SHELF_CSV_COLUMNS
)


def persona_probation_other_export_filename_slug() -> str:
    return "persona_probation_other"


def critique_pairings_operator_summary_export_json(
    summary: Mapping[str, Any],
) -> str:
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), indent=2, ensure_ascii=False)


def critique_pairings_operator_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "has_critique_pairings_yaml": False,
        "producer_taxonomy_key_count": 0,
        "critic_role_entries_total": 0,
        "load_error_present": False,
    }
    if not isinstance(summary, Mapping):
        return metrics
    metrics["has_critique_pairings_yaml"] = summary.get("has_critique_pairings_yaml") is True
    pk = summary.get("producer_taxonomy_key_count")
    if isinstance(pk, int) and not isinstance(pk, bool) and pk >= 0:
        metrics["producer_taxonomy_key_count"] = pk
    total = summary.get("critique_pairing_critic_role_entries_total")
    if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
        metrics["critic_role_entries_total"] = total
    err = summary.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def critique_pairings_operator_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Critique pairings YAML present",
            "value": str(metrics.get("has_critique_pairings_yaml", False)).lower(),
        },
        {
            "field": "Producer taxonomy keys",
            "value": str(metrics.get("producer_taxonomy_key_count", 0)),
        },
        {
            "field": "Critic role entries total",
            "value": str(metrics.get("critic_role_entries_total", 0)),
        },
    ]
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def critique_pairings_operator_summary_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


critique_pairings_operator_summary_operator_metrics_table_rows_csv = field_value_table_rows_csv


def critique_pairings_operator_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("has_critique_pairings_yaml") is not True:
        return None
    if metrics.get("load_error_present") is True:
        return "Critique pairings operator metrics: YAML present with **load error**."
    pk = metrics.get("producer_taxonomy_key_count", 0)
    total = metrics.get("critic_role_entries_total", 0)
    if not isinstance(pk, int) or isinstance(pk, bool):
        pk = 0
    if not isinstance(total, int) or isinstance(total, bool):
        total = 0
    return (
        f"Critique pairings operator metrics: **{pk}** producer key(s), "
        f"**{total}** critic role entr(y/ies)."
    )


def critique_pairings_operator_summary_operator_metrics_export_filename_slug() -> str:
    return "critique_pairings_operator_summary_operator_metrics"


def critique_pairings_export_filename_slug() -> str:
    return "critique_pairings"


_CRITIQUE_PAIRINGS_CRITIC_COUNTS_CSV_COLUMNS: tuple[str, ...] = (
    "producer",
    "critic_roles",
)


def _critique_pairings_critic_counts_rows_from_list(
    raw: Any,
) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        producer = item.get("producer")
        critic_roles = item.get("critic_roles")
        if not isinstance(producer, str) or not producer.strip():
            continue
        out.append(
            {
                "producer": producer.strip(),
                "critic_roles": str(critic_roles) if critic_roles is not None else "",
            },
        )
    return out


def critique_pairings_critic_counts_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    return _critique_pairings_critic_counts_rows_from_list(
        summary.get("critique_pairing_critic_counts_by_producer_sample"),
    )


def critique_pairings_critic_counts_all_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    full = summary.get("critique_pairing_critic_counts_by_producer")
    if isinstance(full, list) and full:
        return _critique_pairings_critic_counts_rows_from_list(full)
    return critique_pairings_critic_counts_table_rows(summary)


def critique_pairings_critic_counts_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


critique_pairings_critic_counts_table_rows_csv = partial(
    table_rows_csv, columns=_CRITIQUE_PAIRINGS_CRITIC_COUNTS_CSV_COLUMNS
)


def critique_pairings_critic_counts_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    return critique_pairings_critic_counts_export_json(rows)


critique_pairings_critic_counts_all_table_rows_csv = critique_pairings_critic_counts_table_rows_csv


_CRITIQUE_PAIRINGS_PRODUCER_KEYS_CSV_COLUMNS: tuple[str, ...] = ("producer_key",)


def _critique_pairings_producer_keys_rows_from_list(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for key in raw:
        if isinstance(key, str) and key.strip():
            out.append({"producer_key": key.strip()})
    return out


def critique_pairings_producer_keys_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    return _critique_pairings_producer_keys_rows_from_list(
        summary.get("producer_taxonomy_keys_sample"),
    )


def critique_pairings_producer_keys_all_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    full = summary.get("producer_taxonomy_keys")
    if isinstance(full, list) and full:
        return _critique_pairings_producer_keys_rows_from_list(full)
    return critique_pairings_producer_keys_table_rows(summary)


def critique_pairings_producer_keys_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def critique_pairings_producer_keys_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    return critique_pairings_producer_keys_export_json(rows)


critique_pairings_producer_keys_table_rows_csv = partial(
    table_rows_csv, columns=_CRITIQUE_PAIRINGS_PRODUCER_KEYS_CSV_COLUMNS
)

critique_pairings_producer_keys_all_table_rows_csv = critique_pairings_producer_keys_table_rows_csv
