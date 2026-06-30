from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from nimbusware_console.explainer_core.workflow_metrics_spec import repo_explainer_spec
from nimbusware_console.workflow_explainers.agent_evaluator import metrics as agent_evaluator_metrics
from nimbusware_console.workflow_explainers.escalation_suppress import metrics as escalation_suppress_metrics
from nimbusware_console.workflow_explainers.security_scan_metadata import (
    metrics as security_scan_metadata_metrics,
)
from nimbusware_console.workflow_explainers.self_refinement import metrics as self_refinement_metrics
from nimbusware_console.workflow_explainers.universal_critique import (
    metrics as universal_critique_metrics,
)

_EXPLAINER_CASES: tuple[tuple[str, str, Callable[[Mapping[str, Any] | None], dict[str, Any]]], ...] = (
    (
        "self_refinement",
        "self_refinement_workflow_explainer",
        self_refinement_metrics.self_refinement_workflow_explainer_operator_metrics,
    ),
    (
        "universal_critique",
        "universal_critique_workflow_explainer",
        universal_critique_metrics.universal_critique_workflow_explainer_operator_metrics,
    ),
    (
        "agent_evaluator",
        "agent_evaluator_workflow_explainer",
        agent_evaluator_metrics.agent_evaluator_workflow_explainer_operator_metrics,
    ),
    (
        "escalation_suppress",
        "escalation_suppress_workflow_explainer",
        escalation_suppress_metrics.escalation_suppress_workflow_explainer_operator_metrics,
    ),
    (
        "security_scan_metadata",
        "security_scan_metadata_workflow_explainer",
        security_scan_metadata_metrics.security_scan_metadata_workflow_explainer_operator_metrics,
    ),
)


@pytest.mark.parametrize(("slug", "prefix", "metrics_fn"), _EXPLAINER_CASES)
def test_workflow_explainer_metrics_yaml_spec_roundtrip(
    slug: str,
    prefix: str,
    metrics_fn: Callable[[Mapping[str, Any] | None], dict[str, Any]],
) -> None:
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
    mod = {
        "self_refinement": self_refinement_metrics,
        "universal_critique": universal_critique_metrics,
        "agent_evaluator": agent_evaluator_metrics,
        "escalation_suppress": escalation_suppress_metrics,
        "security_scan_metadata": security_scan_metadata_metrics,
    }[slug]
    assert hasattr(mod, f"{prefix}_operator_metrics_table_rows")
    assert hasattr(mod, f"{prefix}_operator_metrics_caption")
    assert hasattr(mod, f"{prefix}_operator_metrics_export_json")
