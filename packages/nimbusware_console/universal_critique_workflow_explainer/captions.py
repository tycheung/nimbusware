from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.universal_critique_workflow_explainer.compare import (
    universal_critique_env_override_deltas,
)


def universal_critique_yaml_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
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
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_nonempty_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique YAML top-level nonempty value count: **{raw}**."


def universal_critique_yaml_top_level_list_child_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_list_child_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique YAML top-level list child count: **{raw}**."


def universal_critique_yaml_top_level_enabled_true_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_enabled_true_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique YAML top-level enabled: true count: **{raw}**."


def universal_critique_yaml_top_level_enabled_false_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_enabled_false_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique YAML top-level enabled: false count: **{raw}**."


def universal_critique_yaml_top_level_mapping_child_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("universal_critique_yaml_present") is not True:
        return None
    if isinstance(payload.get("load_error"), str) and str(payload.get("load_error")).strip():
        return None
    raw = payload.get("universal_critique_yaml_top_level_mapping_child_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Universal critique YAML top-level mapping child count: **{raw}**."


def universal_critique_workflow_yaml_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
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
    if not isinstance(payload, Mapping):
        return None
    n = len(universal_critique_env_override_deltas(payload))
    if n == 0:
        return "Universal critique: no env overrides differ from workflow YAML."
    word = "override" if n == 1 else "overrides"
    return f"Universal critique: **{n}** env {word} differ from workflow YAML."
