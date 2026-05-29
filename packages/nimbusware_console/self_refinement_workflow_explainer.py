"""Read-only self-refinement workflow + policy summary for Streamlit (PLAN_GAP §14 #17 / fo135)."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import Any

import hermes_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_extensions.self_refinement import (
    SelfRefinementPolicy,
    load_self_refinement_policy,
    self_refinement_policy_from_mapping,
)
from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path
from hermes_orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
)


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _load_policy_or_default(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> tuple[SelfRefinementPolicy, dict[str, Any]]:
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    disk_bytes: int | None = None
    if path.is_file():
        try:
            disk_bytes = int(path.stat().st_size)
        except OSError:
            disk_bytes = None
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        snap: dict[str, Any] = {
            "relpath": "configs/self_refinement/policy.yaml",
            "exists": True,
            "source": "materializer",
        }
        try:
            raw = config_materializer.get_self_refinement_policy()
            pol = self_refinement_policy_from_mapping(raw)
            snap["policy_yaml_file_bytes"] = disk_bytes
            rv = raw.get("version") if isinstance(raw, dict) else None
            snap["policy_yaml_top_level_version_int"] = (
                int(rv) if type(rv) is int and not isinstance(rv, bool) else None
            )
            if snap["policy_yaml_top_level_version_int"] is None and path.is_file():
                try:
                    raw_pol = load_yaml(path)
                    if isinstance(raw_pol, dict):
                        rv_disk = raw_pol.get("version")
                        if type(rv_disk) is int and not isinstance(rv_disk, bool):
                            snap["policy_yaml_top_level_version_int"] = rv_disk
                except (OSError, ValueError, UnicodeDecodeError):
                    pass
            return pol, snap
        except KeyError:
            pol = SelfRefinementPolicy(version=1, enabled=False, description="")
            snap["exists"] = False
            snap["note"] = "missing in materializer — same default as pipeline"
            snap["policy_yaml_file_bytes"] = None
            snap["policy_yaml_top_level_version_int"] = None
            return pol, snap
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    snap: dict[str, Any] = {
        "relpath": "configs/self_refinement/policy.yaml",
        "exists": path.is_file(),
    }
    if not path.is_file():
        pol = SelfRefinementPolicy(version=1, enabled=False, description="")
        snap["note"] = "missing file — same default object as pipeline when policy absent"
        snap["policy_yaml_file_bytes"] = None
        snap["policy_yaml_top_level_version_int"] = None
        return pol, snap
    try:
        snap["policy_yaml_file_bytes"] = int(path.stat().st_size)
    except OSError:
        snap["policy_yaml_file_bytes"] = None
    snap["policy_yaml_top_level_version_int"] = None
    try:
        raw_pol = load_yaml(path)
        if isinstance(raw_pol, dict):
            rv = raw_pol.get("version")
            if type(rv) is int and not isinstance(rv, bool):
                snap["policy_yaml_top_level_version_int"] = rv
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    pol = load_self_refinement_policy(path)
    return pol, snap


def _self_refinement_stage_marker_env_disabled() -> bool:
    raw = os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "").strip().lower()
    return raw in ("0", "false", "no")


def _hermes_self_refinement_ungated_loop_env_summary() -> dict[str, Any]:
    """Mirror ``RunOrchestrator._maybe_emit_self_refinement_stage_marker`` ungated env branch."""
    raw = os.environ.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_on": False,
            "forces_off": False,
            "unset": True,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_on": True,
            "forces_off": False,
            "unset": False,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_on": False,
            "forces_off": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "forces_on": False,
        "forces_off": False,
        "unset": True,
        "unrecognised_value": True,
    }


def self_refinement_ungated_loop_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary of ``HERMES_SELF_REFINEMENT_UNGATED_LOOP`` env gate."""
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_on"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** force-on"
            f"{detail} — overrides workflow ``ungated_loop`` when set."
        )
    if env.get("forces_off"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** force-off"
            f"{detail}."
        )
    if env.get("unset"):
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** unset — "
            "workflow ``self_refinement.ungated_loop`` controls ungated progression."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** "
            f"unrecognised value{detail} — treated like unset."
        )
    return None


def _hermes_self_refinement_stage_marker_env_summary() -> dict[str, Any]:
    """Mirror ``RunOrchestrator._self_refinement_stage_marker_env_disabled``."""
    raw = os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_marker": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_marker": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_marker": False,
        "unset": False,
        "unrecognised_value": True,
    }


def _marker_preview(
    wf_sr: SelfRefinementWorkflowBlock,
    pol: SelfRefinementPolicy,
) -> dict[str, Any]:
    """Match ``RunOrchestrator._maybe_emit_self_refinement_stage_marker`` merge + gate."""
    version = pol.version
    description = pol.description
    if wf_sr.version is not None:
        version = wf_sr.version
    if wf_sr.description is not None:
        description = wf_sr.description
    max_iterations = pol.max_iterations
    if wf_sr.max_iterations is not None:
        max_iterations = wf_sr.max_iterations
    auto_promote = bool(pol.auto_promote_probation or wf_sr.auto_promote_probation)
    bounded = (description or "")[:2000]
    would_emit = bool(pol.enabled or wf_sr.enabled)
    env_off = _self_refinement_stage_marker_env_disabled()
    ap_raw = os.environ.get("HERMES_SELF_REFINEMENT_AUTO_PROMOTE", "").strip().lower()
    auto_promote_env_off = ap_raw in ("0", "false", "no")
    return {
        "would_emit_self_refinement_marker": would_emit,
        "would_emit_marker_after_env": would_emit and not env_off,
        "merged_version": version,
        "merged_description_preview": bounded,
        "merged_description_len": len(bounded),
        "merged_max_iterations": max_iterations,
        "merged_auto_promote_probation": auto_promote,
        "HERMES_SELF_REFINEMENT_STAGE_MARKER": _hermes_self_refinement_stage_marker_env_summary(),
        "HERMES_SELF_REFINEMENT_AUTO_PROMOTE": os.environ.get(
            "HERMES_SELF_REFINEMENT_AUTO_PROMOTE",
            "",
        ).strip()
        or None,
        "auto_promote_after_env": auto_promote and not auto_promote_env_off,
    }


def self_refinement_merged_version_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    """Pipeline-style merged policy version from ``marker_merge``."""
    if not isinstance(marker_merge, Mapping):
        return None
    ver = marker_merge.get("merged_version")
    if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
        return None
    return f"Self-refinement merge preview: version=**{ver}**."


def self_refinement_merged_description_preview_caption(
    marker_merge: Mapping[str, Any] | None,
    *,
    max_chars: int = 120,
) -> str | None:
    """Bounded ``merged_description_preview`` from ``marker_merge``."""
    if not isinstance(marker_merge, Mapping):
        return None
    preview = marker_merge.get("merged_description_preview")
    if not isinstance(preview, str):
        return None
    text = preview.strip()
    if not text:
        return None
    raw_len = marker_merge.get("merged_description_len")
    if isinstance(raw_len, int) and not isinstance(raw_len, bool) and raw_len > 0:
        len_hint = raw_len
    else:
        len_hint = len(text)
    limit = max_chars if max_chars > 0 else 120
    shown = text if len(text) <= limit else text[:limit] + "…"
    return (
        f"Self-refinement merge preview: description ({len_hint} chars): "
        f"`{shown}`."
    )


def self_refinement_would_emit_after_env_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``would_emit_marker_after_env`` from ``marker_merge``."""
    if not isinstance(marker_merge, Mapping):
        return None
    after_env = marker_merge.get("would_emit_marker_after_env")
    if after_env is True:
        return "Self-refinement marker after env: **would emit**."
    if after_env is False:
        return "Self-refinement marker after env: **would not emit**."
    return None


def self_refinement_would_emit_marker_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary of whether a ``self_refinement:policy`` marker would emit after env."""
    if not isinstance(marker_merge, Mapping):
        return None
    after_env = marker_merge.get("would_emit_marker_after_env")
    if after_env is True:
        would = marker_merge.get("would_emit_self_refinement_marker")
        if would is False:
            return (
                "Self-refinement marker: **would emit** after env "
                "(workflow/policy gate on; env kill-switch off)."
            )
        return (
            "Self-refinement marker: **would emit** "
            "``stage.started`` ``self_refinement:policy`` for this profile."
        )
    if after_env is False:
        would = marker_merge.get("would_emit_self_refinement_marker")
        if would is True:
            return (
                "Self-refinement marker: **would not emit** — "
                "**HERMES_SELF_REFINEMENT_STAGE_MARKER** kill-switch active."
            )
        return (
            "Self-refinement marker: **would not emit** "
            "(workflow ``self_refinement`` and disk policy gate off)."
        )
    return None


def self_refinement_workflow_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Python type name of the frozen ``self_refinement`` workflow YAML value."""
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("self_refinement_workflow_yaml_raw_type")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Self-refinement workflow YAML raw type: **{text}**."


def self_refinement_policy_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """On-disk ``configs/self_refinement/policy.yaml`` file size from the explainer."""
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    pol = payload.get("policy_yaml")
    if not isinstance(pol, Mapping):
        return None
    raw = pol.get("policy_yaml_file_bytes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Self-refinement policy.yaml on disk: **{raw}** bytes."


def self_refinement_policy_yaml_disk_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """``version`` int from ``configs/self_refinement/policy.yaml`` when parseable."""
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    pol = payload.get("policy_yaml")
    if not isinstance(pol, Mapping):
        return None
    raw = pol.get("policy_yaml_top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Self-refinement policy.yaml on-disk version: **{raw}**."


def self_refinement_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    """Workflow ``self_refinement`` block + disk policy + pipeline-style merge preview."""
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    mat = console_config_materializer(repo_root)

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    sr_present = False
    sr_yaml_mapping_string_key_count: int | None = None
    sr_workflow_yaml_raw_type: str | None = None

    if wf_sel:
        try:
            disk_raw, _effective_raw, wp, _file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = _relative_under(repo_root, wp)
            raw = disk_raw
            if isinstance(raw, dict) and "self_refinement" in raw:
                block = raw.get("self_refinement")
                if block is not None:
                    sr_workflow_yaml_raw_type = type(block).__name__
                if isinstance(block, dict):
                    sr_yaml_mapping_string_key_count = sum(
                        1 for k in block if isinstance(k, str)
                    )
                sr_present = isinstance(block, dict) and bool(block)
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            load_error = str(exc)

    wf_sr = parse_self_refinement_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    pol, pol_snap = _load_policy_or_default(repo_root, config_materializer=mat)
    pol_snap["enabled"] = pol.enabled
    pol_snap["version"] = pol.version
    pol_snap["description"] = pol.description
    pol_snap["description_char_len"] = len(pol.description or "")

    marker = _marker_preview(wf_sr, pol)

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "load_error": load_error,
        "self_refinement_yaml_present": sr_present,
        "self_refinement_workflow_yaml_raw_type": sr_workflow_yaml_raw_type,
        "self_refinement_yaml_mapping_string_key_count": sr_yaml_mapping_string_key_count,
        "workflow_self_refinement": asdict(wf_sr),
        "policy_yaml": pol_snap,
        "marker_merge": marker,
        "HERMES_SELF_REFINEMENT_UNGATED_LOOP": _hermes_self_refinement_ungated_loop_env_summary(),
    }


def _timeline_self_refinement_description_len(sr: Mapping[str, Any]) -> int:
    desc = sr.get("description")
    if isinstance(desc, str):
        return len(desc)
    if desc is None:
        return 0
    return len(str(desc))


def _version_as_optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def self_refinement_marker_merge_vs_timeline_rows(
    marker_merge: Mapping[str, Any] | None,
    timeline_sr: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Compare explainer ``marker_merge`` to an optional pasted timeline ``self_refinement`` dict.

    Timeline values are **observed** last-marker fields from ``GET /v1/runs/…/timeline``;
    explainer values are **predictive** for the selected workflow profile + current env.
    When the pasted snapshot includes ``marker_count`` (timeline read-model), it is shown
    beside ``—`` in the explainer column (``marker_merge`` does not model session multiplicity).
    """
    mm: Mapping[str, Any] = marker_merge if isinstance(marker_merge, Mapping) else {}
    no_tl = "—"
    tl: Mapping[str, Any] | None = timeline_sr if isinstance(timeline_sr, Mapping) else None

    pre = mm.get("would_emit_self_refinement_marker")
    post = mm.get("would_emit_marker_after_env")
    if tl is None:
        tl_pre = no_tl
    elif tl:
        tl_pre = "snapshot present"
    else:
        tl_pre = "(empty object)"
    tl_post = tl_pre

    expl_ver = mm.get("merged_version")
    tl_ver = tl.get("version") if tl is not None else None
    tl_ver_disp = no_tl if tl is None else ("—" if tl_ver is None else str(tl_ver))
    expl_i = _version_as_optional_int(expl_ver)
    tl_i = _version_as_optional_int(tl_ver) if tl is not None else None
    if tl is None:
        align = no_tl
    elif expl_i is None or tl_i is None:
        align = "n/a (need integer-like versions on both sides)"
    elif expl_i == tl_i:
        align = "match"
    else:
        align = f"mismatch (explainer {expl_i} vs timeline {tl_i})"

    expl_dlen = int(mm.get("merged_description_len") or 0)
    tl_dlen = _timeline_self_refinement_description_len(tl) if tl is not None else 0
    delta = no_tl if tl is None else str(expl_dlen - tl_dlen)

    tl_mc = tl.get("marker_count") if tl is not None else None
    if tl is None:
        tl_mc_disp = no_tl
    elif isinstance(tl_mc, int) and tl_mc >= 0:
        tl_mc_disp = str(tl_mc)
    else:
        tl_mc_disp = "—"

    return [
        {
            "metric": "Would emit marker (workflow ∪ policy)",
            "explainer_marker_merge": str(pre),
            "timeline_self_refinement": tl_pre,
        },
        {
            "metric": "Would emit after env (effective)",
            "explainer_marker_merge": str(post),
            "timeline_self_refinement": tl_post,
        },
        {
            "metric": "Session marker_count (timeline read-model)",
            "explainer_marker_merge": no_tl,
            "timeline_self_refinement": tl_mc_disp,
        },
        {
            "metric": "Version (raw)",
            "explainer_marker_merge": str(expl_ver),
            "timeline_self_refinement": tl_ver_disp,
        },
        {
            "metric": "Version (int) alignment",
            "explainer_marker_merge": align,
            "timeline_self_refinement": no_tl,
        },
        {
            "metric": "Description length (chars)",
            "explainer_marker_merge": str(expl_dlen),
            "timeline_self_refinement": no_tl if tl is None else str(tl_dlen),
        },
        {
            "metric": "Description length delta (explainer − timeline)",
            "explainer_marker_merge": delta,
            "timeline_self_refinement": no_tl,
        },
    ]


def self_refinement_export_filename_slug() -> str:
    """Filename slug prefix for self-refinement explainer exports."""
    return "self_refinement"


_SELF_REFINEMENT_EXPLAINER_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _self_refinement_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def self_refinement_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for self-refinement explainer export."""
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _self_refinement_explainer_cell(payload.get(key)),
            },
        )
    return rows


def self_refinement_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for self-refinement explainer payload."""
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def self_refinement_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize self-refinement explainer field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_EXPLAINER_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_EXPLAINER_CSV_COLUMNS},
            )
    return buf.getvalue()


_SELF_REFINEMENT_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def self_refinement_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`self_refinement_workflow_explainer_payload` (§14 #17)."""
    metrics: dict[str, Any] = {
        "yaml_present": False,
        "yaml_mapping_key_count": 0,
        "policy_enabled": False,
        "policy_version": None,
        "would_emit_marker": False,
        "would_emit_marker_after_env": False,
        "merged_max_iterations": None,
        "ungated_loop_forces_on": False,
        "ungated_loop_forces_off": False,
        "ungated_loop_unset": True,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_present"] = payload.get("self_refinement_yaml_present") is True
    raw_kc = payload.get("self_refinement_yaml_mapping_string_key_count")
    if isinstance(raw_kc, int) and not isinstance(raw_kc, bool) and raw_kc >= 0:
        metrics["yaml_mapping_key_count"] = raw_kc
    pol = payload.get("policy_yaml")
    if isinstance(pol, dict):
        metrics["policy_enabled"] = pol.get("enabled") is True
        ver = pol.get("version")
        if isinstance(ver, int) and not isinstance(ver, bool):
            metrics["policy_version"] = ver
    mm = payload.get("marker_merge")
    if isinstance(mm, dict):
        metrics["would_emit_marker"] = mm.get("would_emit_self_refinement_marker") is True
        metrics["would_emit_marker_after_env"] = (
            mm.get("would_emit_marker_after_env") is True
        )
    merged = payload.get("merged_max_iterations")
    if isinstance(merged, int) and not isinstance(merged, bool) and merged >= 0:
        metrics["merged_max_iterations"] = merged
    ul = payload.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP")
    if isinstance(ul, dict):
        metrics["ungated_loop_forces_on"] = ul.get("forces_on") is True
        metrics["ungated_loop_forces_off"] = ul.get("forces_off") is True
        metrics["ungated_loop_unset"] = ul.get("unset") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def self_refinement_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "YAML present", "value": str(metrics.get("yaml_present", False)).lower()},
        {
            "field": "YAML mapping keys",
            "value": str(metrics.get("yaml_mapping_key_count", 0)),
        },
        {"field": "Policy enabled", "value": str(metrics.get("policy_enabled", False)).lower()},
        {
            "field": "Would emit marker",
            "value": str(metrics.get("would_emit_marker", False)).lower(),
        },
        {
            "field": "Would emit after env",
            "value": str(metrics.get("would_emit_marker_after_env", False)).lower(),
        },
    ]
    merged = metrics.get("merged_max_iterations")
    if isinstance(merged, int) and not isinstance(merged, bool):
        rows.append({"field": "Merged max iterations", "value": str(merged)})
    rows.extend(
        [
        {
            "field": "Ungated loop forces on",
            "value": str(metrics.get("ungated_loop_forces_on", False)).lower(),
        },
        {
            "field": "Ungated loop forces off",
            "value": str(metrics.get("ungated_loop_forces_off", False)).lower(),
        },
    ])
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        rows.append({"field": "Merged max iterations", "value": str(merged_max)})
    ver = metrics.get("policy_version")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Policy version", "value": str(ver)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def self_refinement_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of workflow explainer operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def self_refinement_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize self-refinement workflow explainer operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SELF_REFINEMENT_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def self_refinement_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption for self-refinement workflow explainer metrics."""
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("would_emit_marker_after_env") is True:
        parts.append("marker **would emit** (after env)")
    elif metrics.get("would_emit_marker") is True:
        parts.append("marker **would emit**")
    if metrics.get("ungated_loop_forces_on") is True:
        parts.append("ungated loop env **forces on**")
    elif metrics.get("ungated_loop_forces_off") is True:
        parts.append("ungated loop env **forces off**")
    if metrics.get("policy_enabled") is True:
        parts.append("policy enabled")
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        parts.append(f"max iterations **{merged_max}**")
    elif metrics.get("yaml_present") is True:
        parts.append("YAML block present")
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        parts.append(f"max iterations **{merged_max}**")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    if not parts:
        return None
    return "Self-refinement explainer metrics: " + ", ".join(parts) + "."


def self_refinement_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    """Stable slug for self-refinement workflow explainer operator metrics downloads."""
    return "self_refinement_workflow_explainer_operator_metrics"


def self_refinement_marker_merge_compare_export_filename_slug() -> str:
    """Filename slug prefix for marker_merge vs timeline compare exports."""
    return "self_refinement_marker_compare"


def self_refinement_marker_merge_compare_snapshot(
    marker_merge: Mapping[str, Any] | None,
    timeline_sr: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Snapshot for marker_merge vs pasted timeline (matches Raw JSON expander)."""
    return {
        "marker_merge": marker_merge if isinstance(marker_merge, Mapping) else None,
        "timeline_self_refinement": (
            timeline_sr if isinstance(timeline_sr, Mapping) else None
        ),
    }


def self_refinement_marker_merge_compare_export_json(
    snapshot: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for marker_merge vs timeline compare snapshot."""
    if not isinstance(snapshot, Mapping):
        return "{}"
    return json.dumps(dict(snapshot), indent=2, ensure_ascii=False)


_MARKER_MERGE_COMPARE_CSV_COLUMNS: tuple[str, ...] = (
    "metric",
    "explainer_marker_merge",
    "timeline_self_refinement",
)


def self_refinement_marker_merge_compare_export_json_rows(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Pretty JSON for marker_merge vs timeline comparison table rows."""
    out = [dict(r) for r in rows if isinstance(r, Mapping)]
    return json.dumps(out, indent=2, ensure_ascii=False)


def self_refinement_marker_merge_compare_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize marker_merge vs timeline comparison rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_MARKER_MERGE_COMPARE_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _MARKER_MERGE_COMPARE_CSV_COLUMNS},
            )
    return buf.getvalue()
