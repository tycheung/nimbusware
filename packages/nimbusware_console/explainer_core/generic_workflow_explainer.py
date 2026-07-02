from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from nimbusware_console.explainer_core import explainer_caption_parts
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)

CaptionPartsFn = Callable[[Mapping[str, Any]], list[str]]

_CAPTION_ATTRS: dict[str, str] = {
    "agent_evaluator": "agent_evaluator_caption_parts",
    "escalation_suppress": "escalation_suppress_caption_parts",
    "universal_critique": "universal_critique_caption_parts",
    "security_scan_metadata": "security_scan_metadata_caption_parts",
    "self_refinement": "self_refinement_caption_parts",
}


def _caption_parts_for_slug(slug: str) -> CaptionPartsFn:
    attr = _CAPTION_ATTRS.get(slug)
    if attr is None:
        msg = f"unknown workflow explainer slug: {slug!r}"
        raise KeyError(msg)
    fn = getattr(explainer_caption_parts, attr, None)
    if fn is None:
        msg = f"missing caption parts for workflow explainer slug: {slug!r}"
        raise AttributeError(msg)
    return cast(CaptionPartsFn, fn)


def install_explainer_metrics(slug: str, namespace: dict[str, object]) -> None:
    install_workflow_metrics_from_spec(
        namespace,
        repo_explainer_spec(slug),
        caption_parts_fn=_caption_parts_for_slug(slug),
    )
