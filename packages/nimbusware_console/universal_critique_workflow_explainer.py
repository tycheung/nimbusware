"""Read-only ``universal_critique`` workflow summary for Streamlit (PLAN_GAP §14 #16 / fo134)."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import Any

import hermes_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_orchestrator.workflow_profiles import workflow_profile_path
from hermes_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
)


def _universal_critique_yaml_value_nonempty(value: Any) -> bool:
    """True when a frozen ``universal_critique`` subtree value is not an empty shell."""
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def _universal_critique_top_level_nonempty_count(uc: Mapping[str, Any]) -> int:
    return sum(1 for v in uc.values() if _universal_critique_yaml_value_nonempty(v))


def _universal_critique_top_level_enabled_true_count(uc: Mapping[str, Any]) -> int:
    """Count top-level ``universal_critique`` children that are mappings with ``enabled: true``."""
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and v.get("enabled") is True
    )


def _universal_critique_top_level_enabled_false_count(uc: Mapping[str, Any]) -> int:
    """Count top-level children that are mappings with explicit ``enabled: false``."""
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and v.get("enabled") is False
    )


def _universal_critique_top_level_mapping_child_count(uc: Mapping[str, Any]) -> int:
    """Count top-level ``universal_critique`` children that are YAML mappings (incl. ``{}``)."""
    return sum(1 for v in uc.values() if isinstance(v, dict))


def _universal_critique_top_level_scalar_leaf_count(uc: Mapping[str, Any]) -> int:
    """Count top-level children that are not mappings or lists (YAML scalars / null)."""
    return sum(1 for v in uc.values() if not isinstance(v, (dict, list)))


def _universal_critique_top_level_list_child_count(uc: Mapping[str, Any]) -> int:
    """Count top-level ``universal_critique`` children that are YAML sequences."""
    return sum(1 for v in uc.values() if isinstance(v, list))


def _universal_critique_top_level_enabled_unset_mapping_count(uc: Mapping[str, Any]) -> int:
    """Count top-level mapping children with no ``enabled`` key (stage knob unset in YAML)."""
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and "enabled" not in v
    )


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def universal_critique_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    """YAML-only vs env-resolved ``universal_critique`` knobs for the selected profile."""
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    universal_critique_workflow_yaml_bytes: int | None = None
    universal_critique_yaml_present = False
    universal_critique_yaml_top_level_keys: list[str] = []
    universal_critique_yaml_top_level_nonempty_count = 0
    universal_critique_yaml_top_level_enabled_true_count = 0
    universal_critique_yaml_top_level_enabled_false_count = 0
    universal_critique_yaml_top_level_mapping_child_count = 0
    universal_critique_yaml_top_level_scalar_leaf_count = 0
    universal_critique_yaml_top_level_list_child_count = 0
    universal_critique_yaml_top_level_enabled_unset_mapping_count = 0

    mat = console_config_materializer(repo_root)
    if wf_sel:
        try:
            disk_raw, _effective_raw, wp, file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = _relative_under(repo_root, wp)
            universal_critique_workflow_yaml_bytes = file_bytes
            uc = disk_raw.get("universal_critique")
            if isinstance(uc, dict):
                universal_critique_yaml_top_level_keys = sorted(str(k) for k in uc)
                universal_critique_yaml_present = bool(uc)
                universal_critique_yaml_top_level_nonempty_count = (
                    _universal_critique_top_level_nonempty_count(uc)
                )
                universal_critique_yaml_top_level_enabled_true_count = (
                    _universal_critique_top_level_enabled_true_count(uc)
                )
                universal_critique_yaml_top_level_enabled_false_count = (
                    _universal_critique_top_level_enabled_false_count(uc)
                )
                universal_critique_yaml_top_level_mapping_child_count = (
                    _universal_critique_top_level_mapping_child_count(uc)
                )
                universal_critique_yaml_top_level_scalar_leaf_count = (
                    _universal_critique_top_level_scalar_leaf_count(uc)
                )
                universal_critique_yaml_top_level_list_child_count = (
                    _universal_critique_top_level_list_child_count(uc)
                )
                universal_critique_yaml_top_level_enabled_unset_mapping_count = (
                    _universal_critique_top_level_enabled_unset_mapping_count(uc)
                )
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            load_error = str(exc)

    wf_block = parse_universal_critique_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    eff = effective_universal_critique(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "load_error": load_error,
        "universal_critique_workflow_yaml_bytes": universal_critique_workflow_yaml_bytes,
        "universal_critique_yaml_present": universal_critique_yaml_present,
        "universal_critique_yaml_top_level_keys": universal_critique_yaml_top_level_keys,
        "universal_critique_yaml_top_level_nonempty_count": (
            universal_critique_yaml_top_level_nonempty_count
        ),
        "universal_critique_yaml_top_level_enabled_true_count": (
            universal_critique_yaml_top_level_enabled_true_count
        ),
        "universal_critique_yaml_top_level_enabled_false_count": (
            universal_critique_yaml_top_level_enabled_false_count
        ),
        "universal_critique_yaml_top_level_mapping_child_count": (
            universal_critique_yaml_top_level_mapping_child_count
        ),
        "universal_critique_yaml_top_level_scalar_leaf_count": (
            universal_critique_yaml_top_level_scalar_leaf_count
        ),
        "universal_critique_yaml_top_level_list_child_count": (
            universal_critique_yaml_top_level_list_child_count
        ),
        "universal_critique_yaml_top_level_enabled_unset_mapping_count": (
            universal_critique_yaml_top_level_enabled_unset_mapping_count
        ),
        "yaml_only": asdict(wf_block),
        "effective_with_env": asdict(eff),
    }


def universal_critique_yaml_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Whether the workflow profile carries a ``universal_critique`` mapping."""
    if not isinstance(payload, Mapping):
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return "Universal critique: workflow YAML block **absent** on this profile."
    raw_keys = payload.get("universal_critique_yaml_top_level_keys")
    if isinstance(raw_keys, list) and raw_keys:
        n = len(raw_keys)
        suffix = "stage key" if n == 1 else "stage keys"
        return f"Universal critique: workflow YAML block **present** with **{n}** {suffix}."
    return "Universal critique: workflow YAML block **present**."


def universal_critique_default_enabled_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Caption for ``default_enabled`` YAML knob and effective panel flags."""
    if not isinstance(payload, Mapping):
        return None
    yaml_only = payload.get("yaml_only")
    eff = payload.get("effective_with_env")
    if not isinstance(yaml_only, Mapping) or not isinstance(eff, Mapping):
        return None
    default_on = yaml_only.get("default_enabled") is True
    if not default_on:
        return (
            "Universal critique: ``default_enabled`` is **off** "
            "(panels need explicit ``enabled`` or env gates)."
        )
    impl_on = bool(eff.get("impl_llm")) or bool(eff.get("impl_stub"))
    tw_on = bool(eff.get("tw_enabled"))
    pll_on = bool(eff.get("pll_enabled"))
    return (
        "Universal critique: ``default_enabled`` **on** — effective "
        f"implementation={impl_on}, test_writer={tw_on}, planner={pll_on}."
    )


def universal_critique_workflow_yaml_relpath_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Repo-relative workflow profile path from the explainer payload."""
    if not isinstance(payload, Mapping):
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("workflow_yaml_relpath")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Universal critique workflow YAML: `{text}`."


def universal_critique_yaml_top_level_nonempty_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Top-level ``universal_critique`` subtree count with a non-empty YAML value."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_nonempty_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Universal critique YAML top-level nonempty value count: "
        f"**{raw}**."
    )


def universal_critique_yaml_top_level_list_child_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Count of top-level ``universal_critique`` YAML list-valued children."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_list_child_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Universal critique YAML top-level list child count: "
        f"**{raw}**."
    )


def universal_critique_yaml_top_level_enabled_true_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Count of ``universal_critique`` YAML subtrees with ``enabled: true``."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_enabled_true_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Universal critique YAML top-level enabled: true count: "
        f"**{raw}**."
    )


def universal_critique_yaml_top_level_enabled_false_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Count of ``universal_critique`` YAML subtrees with explicit ``enabled: false``."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_enabled_false_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Universal critique YAML top-level enabled: false count: "
        f"**{raw}**."
    )


def universal_critique_yaml_top_level_mapping_child_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Count of top-level ``universal_critique`` YAML mapping-valued children."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_mapping_child_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Universal critique YAML top-level mapping child count: "
        f"**{raw}**."
    )


def universal_critique_workflow_yaml_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """On-disk workflow YAML file size from the explainer payload."""
    if not isinstance(payload, Mapping):
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_workflow_yaml_bytes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique workflow YAML file: **{raw}** bytes."


def universal_critique_yaml_enabled_bucket_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Compact enabled-bucket rollup from workflow YAML (true / false / unset mapping)."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    true_n = payload.get("universal_critique_yaml_top_level_enabled_true_count")
    false_n = payload.get("universal_critique_yaml_top_level_enabled_false_count")
    unset_n = payload.get("universal_critique_yaml_top_level_enabled_unset_mapping_count")
    if (
        not isinstance(true_n, int)
        or isinstance(true_n, bool)
        or not isinstance(false_n, int)
        or isinstance(false_n, bool)
        or not isinstance(unset_n, int)
        or isinstance(unset_n, bool)
    ):
        return None
    if (true_n + false_n + unset_n) == 0:
        return None
    return (
        "Universal critique YAML enabled buckets: "
        f"**{true_n}** true, **{false_n}** false, **{unset_n}** unset mapping(s)."
    )


_UNIVERSAL_CRITIQUE_STAGE_KEYS_CAP = 6


def universal_critique_yaml_stage_keys_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Sorted top-level stage key names under workflow ``universal_critique``."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw_keys = payload.get("universal_critique_yaml_top_level_keys")
    if not isinstance(raw_keys, list) or not raw_keys:
        return None
    names: list[str] = []
    for item in raw_keys:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text and text not in names:
            names.append(text)
    if not names:
        return None
    names.sort()
    if len(names) <= _UNIVERSAL_CRITIQUE_STAGE_KEYS_CAP:
        body = ", ".join(names)
    else:
        head = names[:_UNIVERSAL_CRITIQUE_STAGE_KEYS_CAP]
        rest = len(names) - _UNIVERSAL_CRITIQUE_STAGE_KEYS_CAP
        body = ", ".join(head) + f", +{rest} more"
    return f"Universal critique YAML stages: {body}."


def universal_critique_enabled_stages_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary of ``enabled: true`` / ``false`` / unset stage subtrees in workflow YAML."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    true_n = payload.get("universal_critique_yaml_top_level_enabled_true_count")
    false_n = payload.get("universal_critique_yaml_top_level_enabled_false_count")
    unset_n = payload.get("universal_critique_yaml_top_level_enabled_unset_mapping_count")
    if (
        not isinstance(true_n, int)
        or isinstance(true_n, bool)
        or not isinstance(false_n, int)
        or isinstance(false_n, bool)
        or not isinstance(unset_n, int)
        or isinstance(unset_n, bool)
    ):
        return None
    t_count = true_n
    f_count = false_n
    u_count = unset_n
    if (t_count + f_count + u_count) == 0:
        return None
    keys = payload.get("universal_critique_yaml_top_level_keys")
    key_note = ""
    if isinstance(keys, list) and keys:
        key_note = f" (top-level keys: {', '.join(str(k) for k in keys)})"
    return (
        f"Universal critique YAML: **{t_count}** stage(s) with ``enabled: true``, "
        f"**{f_count}** with ``enabled: false``, **{u_count}** mapping(s) without ``enabled``"
        f"{key_note}."
    )


def universal_critique_env_override_summary_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line count of env-vs-YAML boolean deltas for universal critique."""
    if not isinstance(payload, Mapping):
        return None
    n = len(universal_critique_env_override_deltas(payload))
    if n == 0:
        return "Universal critique: no env overrides differ from workflow YAML."
    word = "override" if n == 1 else "overrides"
    return f"Universal critique: **{n}** env {word} differ from workflow YAML."


def universal_critique_workflow_vs_timeline_rows(
    explainer_payload: Mapping[str, Any] | None,
    timeline_uc: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Compare workflow explainer rollup to pasted ``universal_critique`` timeline snapshot."""
    exp: Mapping[str, Any] = (
        explainer_payload if isinstance(explainer_payload, Mapping) else {}
    )
    no_tl = "—"
    tl: Mapping[str, Any] | None = (
        timeline_uc if isinstance(timeline_uc, Mapping) else None
    )

    wf_enabled = exp.get("universal_critique_yaml_top_level_enabled_true_count")
    wf_enabled_disp = (
        no_tl
        if not isinstance(wf_enabled, int) or isinstance(wf_enabled, bool)
        else str(wf_enabled)
    )

    if tl is None:
        tl_stage_disp = no_tl
        tl_fail_disp = no_tl
    else:
        sc = tl.get("stage_count")
        tl_stage_disp = (
            no_tl if not isinstance(sc, int) or isinstance(sc, bool) else str(sc)
        )
        fc = tl.get("fail_count")
        tl_fail_disp = (
            no_tl if not isinstance(fc, int) or isinstance(fc, bool) else str(fc)
        )

    align = no_tl
    if tl is not None and isinstance(wf_enabled, int) and not isinstance(wf_enabled, bool):
        sc_i = tl.get("stage_count")
        if isinstance(sc_i, int) and not isinstance(sc_i, bool):
            if wf_enabled == sc_i:
                align = "stage_count matches enabled:true count"
            else:
                align = f"mismatch (workflow enabled:true={wf_enabled} vs timeline stages={sc_i})"

    return [
        {
            "metric": "YAML stages with enabled: true",
            "workflow_explainer": wf_enabled_disp,
            "timeline_universal_critique": tl_stage_disp,
        },
        {
            "metric": "FAIL gate count (timeline)",
            "workflow_explainer": no_tl,
            "timeline_universal_critique": tl_fail_disp,
        },
        {
            "metric": "Alignment note",
            "workflow_explainer": no_tl,
            "timeline_universal_critique": align,
        },
    ]


def universal_critique_env_override_deltas(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    """Rows where ``HERMES_*`` env overrides diverge from frozen workflow YAML booleans."""
    yo = payload.get("yaml_only")
    eff = payload.get("effective_with_env")
    if not isinstance(yo, dict) or not isinstance(eff, dict):
        return []
    rows: list[dict[str, str]] = []
    for k in sorted(yo.keys()):
        if k not in eff:
            continue
        yv, ev = yo[k], eff[k]
        if yv != ev:
            rows.append(
                {"knob": k, "yaml_only": str(yv), "effective_with_env": str(ev)},
            )
    return rows


def universal_critique_export_filename_slug() -> str:
    """Filename slug prefix for universal critique explainer exports."""
    return "universal_critique"


_UNIVERSAL_CRITIQUE_EXPLAINER_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _universal_critique_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def universal_critique_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for universal critique explainer export."""
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _universal_critique_explainer_cell(payload.get(key)),
            },
        )
    return rows


def universal_critique_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for universal critique explainer payload."""
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def universal_critique_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize universal critique explainer field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_UNIVERSAL_CRITIQUE_EXPLAINER_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _UNIVERSAL_CRITIQUE_EXPLAINER_CSV_COLUMNS},
            )
    return buf.getvalue()


_UNIVERSAL_CRITIQUE_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def universal_critique_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`universal_critique_workflow_explainer_payload` (§14 #16)."""
    metrics: dict[str, Any] = {
        "yaml_present": False,
        "top_level_key_count": 0,
        "enabled_true_count": 0,
        "enabled_false_count": 0,
        "enabled_unset_mapping_count": 0,
        "mapping_child_count": 0,
        "scalar_leaf_count": 0,
        "list_child_count": 0,
        "default_enabled_on": False,
        "unanimous_gate_enforce": False,
        "fw_enabled": False,
        "mi_enabled": False,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_present"] = payload.get("universal_critique_yaml_present") is True
    keys = payload.get("universal_critique_yaml_top_level_keys")
    if isinstance(keys, list):
        metrics["top_level_key_count"] = len(keys)

    def _int_field(key: str) -> int:
        raw = payload.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            return raw
        return 0

    metrics["enabled_true_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_true_count",
    )
    metrics["enabled_false_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_false_count",
    )
    metrics["enabled_unset_mapping_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_unset_mapping_count",
    )
    metrics["mapping_child_count"] = _int_field(
        "universal_critique_yaml_top_level_mapping_child_count",
    )
    metrics["list_child_count"] = _int_field(
        "universal_critique_yaml_top_level_list_child_count",
    )
    metrics["scalar_leaf_count"] = _int_field(
        "universal_critique_yaml_top_level_scalar_leaf_count",
    )
    yaml_only = payload.get("yaml_only")
    if isinstance(yaml_only, Mapping):
        metrics["default_enabled_on"] = yaml_only.get("default_enabled") is True
    eff = payload.get("effective_with_env")
    if isinstance(eff, Mapping):
        metrics["unanimous_gate_enforce"] = eff.get("unanimous_gate_enforce") is True
        metrics["fw_enabled"] = eff.get("fw_enabled") is True
        metrics["mi_enabled"] = eff.get("mi_enabled") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def universal_critique_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    return [
        {"field": "YAML present", "value": str(metrics.get("yaml_present", False)).lower()},
        {"field": "Top-level keys", "value": str(metrics.get("top_level_key_count", 0))},
        {"field": "Enabled true", "value": str(metrics.get("enabled_true_count", 0))},
        {"field": "Enabled false", "value": str(metrics.get("enabled_false_count", 0))},
        {
            "field": "Enabled unset (mapping)",
            "value": str(metrics.get("enabled_unset_mapping_count", 0)),
        },
        {"field": "Mapping children", "value": str(metrics.get("mapping_child_count", 0))},
        {"field": "List children", "value": str(metrics.get("list_child_count", 0))},
        {"field": "Scalar leaves", "value": str(metrics.get("scalar_leaf_count", 0))},
        {
            "field": "default_enabled on",
            "value": str(metrics.get("default_enabled_on", False)).lower(),
        },
        {
            "field": "unanimous_gate_enforce",
            "value": str(metrics.get("unanimous_gate_enforce", False)).lower(),
        },
        {"field": "fw_enabled", "value": str(metrics.get("fw_enabled", False)).lower()},
        {"field": "mi_enabled", "value": str(metrics.get("mi_enabled", False)).lower()},
    ]


def universal_critique_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of workflow explainer operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def universal_critique_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize universal critique workflow explainer operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_UNIVERSAL_CRITIQUE_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _UNIVERSAL_CRITIQUE_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def universal_critique_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when universal critique YAML is present."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("yaml_present") is not True:
        return None
    nkeys = metrics.get("top_level_key_count", 0)
    if not isinstance(nkeys, int) or isinstance(nkeys, bool):
        nkeys = 0
    enabled = metrics.get("enabled_true_count", 0)
    if not isinstance(enabled, int) or isinstance(enabled, bool):
        enabled = 0
    parts = [
        f"**{nkeys}** stage key(s)",
        f"**{enabled}** with ``enabled: true``",
    ]
    if metrics.get("default_enabled_on") is True:
        parts.append("``default_enabled`` **on**")
    if metrics.get("unanimous_gate_enforce") is True:
        parts.append("unanimous gate **on**")
    if metrics.get("fw_enabled") is True:
        parts.append("fw panel **on**")
    if metrics.get("mi_enabled") is True:
        parts.append("mi panel **on**")
    lists = metrics.get("list_child_count", 0)
    if isinstance(lists, int) and not isinstance(lists, bool) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    scalar = metrics.get("scalar_leaf_count", 0)
    if isinstance(scalar, int) and not isinstance(scalar, bool) and scalar > 0:
        parts.append(f"**{scalar}** scalar leaf(es)")
    lists = metrics.get("list_child_count", 0)
    if isinstance(lists, int) and not isinstance(lists, bool) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    return "Universal critique explainer metrics: " + ", ".join(parts) + "."


def universal_critique_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    """Stable slug for universal critique workflow explainer operator metrics downloads."""
    return "universal_critique_workflow_explainer_operator_metrics"
