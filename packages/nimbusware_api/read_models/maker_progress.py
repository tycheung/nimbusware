"""Maker progress read-model shim."""

from __future__ import annotations

from nimbusware_projections.builders.maker_progress import (
    maker_progress_from_events,
    strip_operator_fields,
)

__all__ = ["maker_progress_from_events", "strip_operator_fields"]
