from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from agent_core.yaml_io import load_yaml
from console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    caption_from_parts,
    install_operator_metrics_module,
    table_rows_fn,
)

CaptionPartsFn = Callable[[Mapping[str, Any]], Sequence[str]]


def _tuple_pairs(raw: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[tuple[str, str]] = []
    for row in raw:
        if isinstance(row, (list, tuple)) and len(row) == 2:
            out.append((str(row[0]), str(row[1])))
    return tuple(out)


def _nested_bool_fields(raw: Any) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for block in raw:
        if not isinstance(block, dict):
            continue
        nested_key = block.get("nested_key")
        fields = block.get("fields")
        if isinstance(nested_key, str) and isinstance(fields, list):
            out.append((nested_key, _tuple_pairs(fields)))
    return tuple(out)


def _env_tri_state(raw: Any) -> tuple[Any, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[Any] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, (list, tuple)) and len(item) == 4:
            out.append(tuple(str(x) for x in item))
    return tuple(out)


def _env_flags(raw: Any) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[tuple[str, str, str]] = []
    for row in raw:
        if isinstance(row, (list, tuple)) and len(row) == 3:
            out.append((str(row[0]), str(row[1]), str(row[2])))
    return tuple(out)


def _bool_match_fields(raw: Any) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[tuple[str, str, str]] = []
    for row in raw:
        if isinstance(row, (list, tuple)) and len(row) == 3:
            out.append((str(row[0]), str(row[1]), str(row[2])))
    return tuple(out)


def _build_kwargs_from_spec(build: Mapping[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if build.get("bool_fields"):
        kwargs["bool_fields"] = _tuple_pairs(build["bool_fields"])
    if build.get("int_fields"):
        kwargs["int_fields"] = _tuple_pairs(build["int_fields"])
    if build.get("list_len_fields"):
        kwargs["list_len_fields"] = _tuple_pairs(build["list_len_fields"])
    if build.get("nested_bool_fields"):
        kwargs["nested_bool_fields"] = _nested_bool_fields(build["nested_bool_fields"])
    if build.get("nested_int_fields"):
        kwargs["nested_int_fields"] = _nested_bool_fields(build["nested_int_fields"])
    if build.get("nested_exists"):
        kwargs["nested_exists"] = _tuple_pairs(build["nested_exists"])
    if build.get("float_fields"):
        kwargs["float_fields"] = _tuple_pairs(build["float_fields"])
    if build.get("list_nonempty_flags"):
        kwargs["list_nonempty_flags"] = _tuple_pairs(build["list_nonempty_flags"])
    if build.get("nested_optional_int"):
        nested_opt: list[tuple[str, str, str]] = []
        for row in build["nested_optional_int"]:
            if isinstance(row, (list, tuple)) and len(row) == 3:
                nested_opt.append((str(row[0]), str(row[1]), str(row[2])))
        if nested_opt:
            kwargs["nested_optional_int"] = tuple(nested_opt)
    if build.get("env_tri_state"):
        kwargs["env_tri_state"] = _env_tri_state(build["env_tri_state"])
    if build.get("env_flags"):
        kwargs["env_flags"] = _env_flags(build["env_flags"])
    if build.get("str_present"):
        kwargs["str_present"] = _tuple_pairs(build["str_present"])
    if build.get("str_nonempty"):
        kwargs["str_nonempty"] = _tuple_pairs(build["str_nonempty"])
    if build.get("optional_str"):
        kwargs["optional_str"] = _tuple_pairs(build["optional_str"])
    if build.get("optional_int"):
        kwargs["optional_int"] = _tuple_pairs(build["optional_int"])
    if build.get("bool_match_fields"):
        kwargs["bool_match_fields"] = _bool_match_fields(build["bool_match_fields"])
    if build.get("workflow_yaml_file"):
        kwargs["workflow_yaml_file"] = bool(build["workflow_yaml_file"])
    if build.get("load_error"):
        kwargs["load_error"] = bool(build["load_error"])
    return kwargs


def load_workflow_metrics_spec(path: Path) -> dict[str, Any]:
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        msg = f"workflow metrics spec must be a mapping: {path}"
        raise ValueError(msg)
    return raw


def repo_explainer_spec(name: str) -> Path:
    from env import find_repo_root

    return find_repo_root() / "configs" / "explainers" / f"{name}_metrics.yaml"


def repo_display_spec(name: str) -> Path:
    from env import find_repo_root

    return find_repo_root() / "configs" / "displays" / f"{name}.yaml"


def install_workflow_metrics_from_spec(
    namespace: dict[str, object],
    spec_path: Path,
    *,
    caption_parts_fn: CaptionPartsFn,
    custom_metrics_fn: Any | None = None,
    post_process_metrics_fn: Any | None = None,
    custom_table_rows_fn: Any | None = None,
    custom_caption_fn: Any | None = None,
) -> None:
    spec = load_workflow_metrics_spec(spec_path)
    prefix = str(spec["prefix"])
    defaults = dict(spec.get("defaults") or {})
    table_rows = _tuple_pairs(spec.get("table_rows"))
    build_raw = spec.get("build")
    build: Mapping[str, Any] = build_raw if isinstance(build_raw, dict) else {}
    tro_raw = spec.get("table_rows_options")
    tro: Mapping[str, Any] = tro_raw if isinstance(tro_raw, dict) else {}

    optional_keys = tro.get("optional_metric_keys")
    optional_frozen = (
        frozenset(str(k) for k in optional_keys) if isinstance(optional_keys, list) else frozenset()
    )
    bool_only_keys = tro.get("bool_only_when_true")
    bool_only_frozen = (
        frozenset(str(k) for k in bool_only_keys)
        if isinstance(bool_only_keys, list)
        else frozenset()
    )
    use_include_when = bool(optional_frozen or bool_only_frozen)

    def _include_when(m: Mapping[str, Any], key: str) -> bool:
        if key in bool_only_frozen:
            return m.get(key) is True
        if key in optional_frozen:
            if key == "load_error_present" and m.get("load_error_present") is True:
                return True
            return m.get(key) is not None
        return True

    metrics_fn = custom_metrics_fn
    if metrics_fn is None:
        base_metrics_fn = build_metrics_fn(defaults, **_build_kwargs_from_spec(build))
        if post_process_metrics_fn is not None:
            post_fn = post_process_metrics_fn

            def metrics_fn(payload: Mapping[str, Any] | None) -> dict[str, Any]:
                metrics = base_metrics_fn(payload)
                processed = post_fn(metrics, payload)
                return dict(processed)

        else:
            metrics_fn = base_metrics_fn

    table_fn = custom_table_rows_fn
    if table_fn is None:
        table_fn = table_rows_fn(
            table_rows,
            include_when=_include_when if use_include_when else None,
            append_load_error_row=bool(tro.get("append_load_error_row")),
            exclude_keys=frozenset(str(k) for k in (tro.get("exclude_keys") or [])),
        )

    caption_fn = custom_caption_fn
    if caption_fn is None:
        caption_prefix = str(spec.get("caption_prefix") or f"{prefix}: ")
        caption_fn = caption_from_parts(caption_prefix, caption_parts_fn)

    install_operator_metrics_module(
        namespace,
        module_prefix=prefix,
        metrics=metrics_fn,
        table_rows=table_fn,
        caption=caption_fn,
        export_slug=spec.get("export_slug"),
    )
