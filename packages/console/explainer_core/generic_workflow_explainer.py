from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from console.explainer_core import explainer_caption_parts
from console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)

CaptionPartsFn = Callable[[Mapping[str, Any]], list[str]]


def _caption_parts_for_slug(slug: str) -> CaptionPartsFn:
    attr = f"{slug}_caption_parts"
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
