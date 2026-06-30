from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from nimbusware_console.explainer_core.workflow_explainer_registry import (
    WORKFLOW_EXPLAINER_SPECS,
    explainer_metrics_prefix,
)
from nimbusware_console.explainer_core.workflow_metrics_spec import repo_explainer_spec


def _metrics_fn(slug: str) -> Callable[[Mapping[str, Any] | None], dict[str, Any]]:
    mod = importlib.import_module(f"nimbusware_console.workflow_explainers.{slug}")
    prefix = explainer_metrics_prefix(slug)
    return getattr(mod, f"{prefix}_operator_metrics")


_EXPLAINER_CASES = tuple(
    (spec.slug, explainer_metrics_prefix(spec.slug), _metrics_fn(spec.slug))
    for spec in WORKFLOW_EXPLAINER_SPECS
)


@pytest.mark.parametrize(("slug", "prefix", "metrics_fn"), _EXPLAINER_CASES)
def test_workflow_explainer_metrics_yaml_spec_roundtrip(
    slug: str,
    prefix: str,
    metrics_fn: Callable[[Mapping[str, Any] | None], dict[str, Any]],
) -> None:
    if slug in {"integration_adapter_writer", "integrator_threshold"}:
        pytest.skip("custom metrics install (no YAML spec file)")
    spec_path = repo_explainer_spec(slug)
    assert spec_path.is_file(), f"missing explainer spec: {spec_path}"
    out = metrics_fn(None)
    assert isinstance(out, dict)
    assert out, f"{prefix} defaults must be non-empty"


@pytest.mark.parametrize(("slug", "prefix", "metrics_fn"), _EXPLAINER_CASES)
def test_workflow_explainer_operator_exports_installed(
    slug: str,
    prefix: str,
    metrics_fn: Callable[[Mapping[str, Any] | None], dict[str, Any]],
) -> None:
    mod = importlib.import_module(f"nimbusware_console.workflow_explainers.{slug}")
    assert hasattr(mod, f"{prefix}_operator_metrics_table_rows")
    assert hasattr(mod, f"{prefix}_operator_metrics_caption")
    assert hasattr(mod, f"{prefix}_operator_metrics_export_json")
    out = metrics_fn(None)
    assert isinstance(out, dict) and out


@pytest.mark.parametrize("slug", [spec.slug for spec in WORKFLOW_EXPLAINER_SPECS])
def test_workflow_explainer_payload_fn_importable(slug: str) -> None:
    mod = importlib.import_module(f"nimbusware_console.workflow_explainers.{slug}")
    payload_names = [
        n
        for n in dir(mod)
        if n.endswith("_explainer_payload") or n.endswith("_workflow_explainer_payload")
    ]
    assert payload_names, f"{slug}: expected a payload builder export"
