from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from console.explainer_core.workflow_explainer_registry import (
    WORKFLOW_EXPLAINER_SPECS,
    explainer_metrics_prefix,
)
from unit.composite_repo_fixtures import write_workflow_profile
from unit.workflow_explainer_helpers import (
    explainer_payload_for_slug,
    write_escalation_policy,
)


@dataclass(frozen=True)
class ExplainerExportFns:
    table_rows: Callable[[Mapping[str, Any]], list[dict[str, str]]]
    export_json: Callable[[Mapping[str, Any]], str]
    table_rows_csv: Callable[[list[dict[str, str]]], str]
    export_filename_slug: Callable[[], str]
    operator_metrics: Callable[[Mapping[str, Any] | None], dict[str, Any]]
    operator_metrics_export_json: Callable[[Mapping[str, Any]], str]
    operator_metrics_export_filename_slug: Callable[[], str]
    operator_metrics_table_rows: Callable[[Mapping[str, Any]], list[dict[str, str]]]


def _explainer_short_name(slug: str) -> str:
    if slug == "integrator_threshold":
        return "integrator_threshold_explainer"
    return slug


def load_explainer_export_fns(slug: str) -> ExplainerExportFns:
    mod = importlib.import_module(f"console.workflow_explainers.{slug}")
    short = _explainer_short_name(slug)
    prefix = explainer_metrics_prefix(slug)
    return ExplainerExportFns(
        table_rows=getattr(mod, f"{short}_explainer_table_rows"),
        export_json=getattr(mod, f"{short}_explainer_export_json"),
        table_rows_csv=getattr(mod, f"{short}_explainer_table_rows_csv"),
        export_filename_slug=getattr(mod, f"{short}_export_filename_slug"),
        operator_metrics=getattr(mod, f"{prefix}_operator_metrics"),
        operator_metrics_export_json=getattr(
            mod,
            f"{prefix}_operator_metrics_export_json",
        ),
        operator_metrics_export_filename_slug=getattr(
            mod,
            f"{prefix}_operator_metrics_export_filename_slug",
        ),
        operator_metrics_table_rows=getattr(
            mod,
            f"{prefix}_operator_metrics_table_rows",
        ),
    )


def assert_explainer_export_contract(
    fns: ExplainerExportFns,
    payload: Mapping[str, Any],
    *,
    export_slug: str,
    required_fields: tuple[str, ...] = (),
) -> None:
    rows = fns.table_rows(payload)
    fields = {r["field"] for r in rows}
    for field in required_fields:
        assert field in fields, f"missing field {field!r} in table rows"
    assert len(rows) == len(payload)
    parsed = json.loads(fns.export_json(payload))
    assert parsed == payload
    csv_text = fns.table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert fns.table_rows({}) == []  # type: ignore[arg-type]
    assert fns.table_rows_csv([]) == ""
    assert fns.export_filename_slug() == export_slug


def assert_operator_metrics_export_contract(
    fns: ExplainerExportFns,
    *,
    first_row_field: str | None = None,
    metrics_export_slug_suffix: str | None = None,
) -> None:
    m = fns.operator_metrics({})
    roundtrip = json.loads(fns.operator_metrics_export_json(m))
    assert roundtrip == m
    rows = fns.operator_metrics_table_rows(m)
    if first_row_field is not None:
        assert rows[0]["field"] == first_row_field
    slug = fns.export_filename_slug()
    expected = metrics_export_slug_suffix or f"{slug}_workflow_explainer_operator_metrics"
    assert fns.operator_metrics_export_filename_slug() == expected


def load_caption_fn(dotted: str) -> Callable[[Any], str | None]:
    module_path, _, name = dotted.rpartition(".")
    mod = importlib.import_module(module_path)
    fn = getattr(mod, name)
    if not callable(fn):
        raise TypeError(f"{dotted} is not callable")
    return fn


EXPORT_SMOKE_SLUGS = tuple(
    spec.slug
    for spec in WORKFLOW_EXPLAINER_SPECS
    if spec.slug not in {"integration_adapter_writer", "integrator_threshold"}
)


def load_explainer_cases_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"expected mapping in {path}")
    return raw


def resolve_explainer_caption_fn(slug: str, fn_name: str) -> Callable[[Any], str | None]:
    return load_caption_fn(f"console.workflow_explainers.{slug}.{fn_name}")


def load_operator_metrics_fns(
    slug: str,
) -> tuple[
    Callable[[Mapping[str, Any] | None], dict[str, Any]],
    Callable[[Mapping[str, Any]], str | None],
]:
    prefix = explainer_metrics_prefix(slug)
    mod = importlib.import_module(f"console.workflow_explainers.{slug}")
    return (
        getattr(mod, f"{prefix}_operator_metrics"),
        getattr(mod, f"{prefix}_operator_metrics_caption"),
    )


def setup_explainer_repo(tmp_path: Path, case: Mapping[str, Any]) -> None:
    profile = str(case.get("workflow_profile", "wf"))
    if "workflow_yaml" in case:
        write_workflow_profile(tmp_path, profile, str(case["workflow_yaml"]))
    if "policy_yaml" in case:
        write_escalation_policy(tmp_path, str(case["policy_yaml"]))


def run_explainer_payload_case(
    slug: str,
    case: Mapping[str, Any],
    tmp_path: Path,
) -> dict[str, Any]:
    setup_explainer_repo(tmp_path, case)
    profile = str(case.get("workflow_profile", "wf"))
    return explainer_payload_for_slug(tmp_path, slug, profile)


def assert_payload_expectations(
    payload: Mapping[str, Any],
    case: Mapping[str, Any],
) -> None:
    expect = case.get("expect") or {}
    for key, expected in expect.items():
        assert payload[key] == expected, f"{case.get('id', '?')}: {key}"
    for key in case.get("expect_nonempty_str") or ():
        value = payload[key]
        assert isinstance(value, str) and value.strip() != "", (
            f"{case.get('id', '?')}: {key} expected non-empty str"
        )
    for key, type_name in (case.get("expect_type") or {}).items():
        value = payload[key]
        if type_name == "str":
            assert isinstance(value, str), f"{case.get('id', '?')}: {key}"
        elif type_name == "int":
            assert isinstance(value, int), f"{case.get('id', '?')}: {key}"
        elif type_name == "list":
            assert isinstance(value, list), f"{case.get('id', '?')}: {key}"
        else:
            raise ValueError(f"unsupported expect_type: {type_name!r}")
    for key, bound in (case.get("expect_int_range") or {}).items():
        value = payload[key]
        assert isinstance(value, int), f"{case.get('id', '?')}: {key}"
        if "min" in bound:
            assert value >= bound["min"], f"{case.get('id', '?')}: {key}"
        if "max" in bound:
            assert value <= bound["max"], f"{case.get('id', '?')}: {key}"
    for key, nested in (case.get("expect_nested") or {}).items():
        value = payload[key]
        assert isinstance(value, dict), f"{case.get('id', '?')}: {key}"
        for sub_key, expected in nested.items():
            assert value.get(sub_key) == expected, f"{case.get('id', '?')}: {key}.{sub_key}"
    for key in case.get("expect_get_null") or ():
        assert payload.get(key) is None, f"{case.get('id', '?')}: {key}"


def assert_caption_expectations(
    result: str | None,
    expect: Mapping[str, Any],
    *,
    case_id: str = "?",
) -> None:
    if expect.get("null"):
        assert result is None, case_id
        return
    if expect.get("not_null"):
        assert result is not None, case_id
    if "eq" in expect:
        assert result == expect["eq"], case_id
    if result is not None:
        for fragment in expect.get("contains") or ():
            needle = str(fragment).lower() if isinstance(fragment, bool) else str(fragment)
            haystack = result.lower() if isinstance(fragment, bool) else result
            assert needle in haystack, f"{case_id}: missing {fragment!r} in {result!r}"
        if "icontains" in expect:
            assert expect["icontains"].lower() in result.lower(), case_id
        if "startswith" in expect:
            assert result.startswith(expect["startswith"]), case_id
        if "endswith" in expect:
            assert result.endswith(expect["endswith"]), case_id


def run_caption_case(
    slug: str,
    case: Mapping[str, Any],
    tmp_path: Path | None = None,
) -> str | None:
    fn = resolve_explainer_caption_fn(slug, str(case["fn"]))
    payload = case.get("payload")
    if (
        payload is None
        and tmp_path is not None
        and ("workflow_yaml" in case or "policy_yaml" in case)
    ):
        payload = run_explainer_payload_case(slug, case, tmp_path)
    return fn(payload)


def run_and_assert_caption_case(
    slug: str,
    case: Mapping[str, Any],
    tmp_path: Path | None = None,
) -> None:
    if "payload" in case:
        payload = case["payload"]
    elif tmp_path is not None and ("workflow_yaml" in case or "policy_yaml" in case):
        payload = run_explainer_payload_case(slug, case, tmp_path)
        if case.get("expect_payload"):
            assert_payload_expectations(
                payload,
                {"expect": case["expect_payload"], "id": case.get("id", "?")},
            )
    else:
        raise ValueError(f"caption case {case.get('id', '?')} needs payload or repo setup")
    fn = resolve_explainer_caption_fn(slug, str(case["fn"]))
    result = fn(payload)
    assert_caption_expectations(result, case.get("expect") or {}, case_id=str(case.get("id", "?")))


def run_and_assert_operator_metrics_case(slug: str, case: Mapping[str, Any]) -> None:
    metrics_fn, caption_fn = load_operator_metrics_fns(slug)
    payload = case.get("payload") or {}
    metrics = metrics_fn(payload)
    for key, expected in (case.get("expect_metrics") or {}).items():
        assert metrics[key] == expected, f"{case.get('id', '?')}: metrics[{key}]"
    cap = caption_fn(metrics)
    expect_cap = case.get("expect_caption") or {}
    if expect_cap.get("null"):
        assert cap is None, case.get("id")
    elif expect_cap.get("not_null"):
        assert cap is not None, case.get("id")
    if cap is not None:
        for fragment in expect_cap.get("contains") or ():
            needle = str(fragment).lower() if isinstance(fragment, bool) else str(fragment)
            haystack = cap.lower() if isinstance(fragment, bool) else cap
            assert needle in haystack, f"{case.get('id', '?')}: caption missing {fragment!r}"
        if "icontains" in expect_cap:
            assert expect_cap["icontains"].lower() in cap.lower(), case.get("id")


def run_and_assert_env_payload_case(
    slug: str,
    case: Mapping[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in (case.get("env") or {}).items():
        monkeypatch.setenv(key, str(value))
    payload = run_explainer_payload_case(slug, case, tmp_path)
    assert_payload_expectations(payload, case)


def decode_caption_guard_input(value: Any) -> Any:
    if value == "null":
        return None
    return value


def caption_guard_bad_payload_matrix(raw: Mapping[str, Any]) -> list[tuple[str, Any]]:
    return [
        (str(row["fn"]), decode_caption_guard_input(inp))
        for row in raw.get("bad_payload") or []
        for inp in row.get("inputs") or []
    ]


def caption_guard_load_error_matrix(
    raw: Mapping[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    return [(str(row["fn"]), dict(row["payload"])) for row in raw.get("load_error_payload") or []]


def assert_caption_guard_returns_none(fn_path: str, payload: Any) -> None:
    assert load_caption_fn(fn_path)(payload) is None


def assert_caption_guard_tmp_path_load_error(row: Mapping[str, Any], tmp_path: Path) -> None:
    from unit.workflow_explainer_helpers import escalation_explainer_payload

    fn = load_caption_fn(str(row["fn"]))
    if row.get("setup") == "malformed_escalation_policy":
        pl = escalation_explainer_payload(
            tmp_path,
            policy_yaml=": : not yaml\n",
        )
        assert isinstance(pl["escalation_policy_yaml_load_error"], str)
        assert fn(pl) is None
        return
    raise ValueError(f"unsupported caption guard setup: {row.get('setup')!r}")
