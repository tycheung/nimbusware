from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from nimbusware_console.explainer_core.explainer_caption_parts import (
    agent_evaluator_caption_parts,
    escalation_suppress_caption_parts,
    security_scan_metadata_caption_parts,
    self_refinement_caption_parts,
    universal_critique_caption_parts,
)
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)

CaptionPartsFn = Callable[[Mapping[str, Any]], list[str]]

_YAML_EXPLAINERS: dict[str, CaptionPartsFn] = {
    "agent_evaluator": agent_evaluator_caption_parts,
    "escalation_suppress": escalation_suppress_caption_parts,
    "universal_critique": universal_critique_caption_parts,
    "security_scan_metadata": security_scan_metadata_caption_parts,
    "self_refinement": self_refinement_caption_parts,
}


def install_explainer_metrics(slug: str, namespace: dict[str, object]) -> None:
    caption_parts = _YAML_EXPLAINERS.get(slug)
    if caption_parts is None:
        msg = f"unknown workflow explainer slug: {slug!r}"
        raise KeyError(msg)
    install_workflow_metrics_from_spec(
        namespace,
        repo_explainer_spec(slug),
        caption_parts_fn=caption_parts,
    )
