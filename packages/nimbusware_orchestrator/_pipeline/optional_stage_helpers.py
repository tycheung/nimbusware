"""Backward-compatible re-export — helpers live in ``_helpers.py`` for pipeline globals."""

from nimbusware_orchestrator._pipeline._helpers import (
    optional_meta_section,
    optional_rows_and_profile,
    optional_tri_allows_emit,
)

__all__ = [
    "optional_meta_section",
    "optional_rows_and_profile",
    "optional_tri_allows_emit",
]
