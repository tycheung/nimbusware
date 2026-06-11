from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PREVIEW_EFFECTIVE_MIN_SCORE_KEY = "preview_effective_min_score_to_pass"
LEGACY_PREVIEW_EFFECTIVE_MIN_SCORE_KEY = "streamlit_preview_effective_min_score_to_pass"


def get_preview_effective_min_score(payload: Mapping[str, Any] | None) -> Any:
    if not isinstance(payload, Mapping):
        return None
    value = payload.get(PREVIEW_EFFECTIVE_MIN_SCORE_KEY)
    if value is not None:
        return value
    return payload.get(LEGACY_PREVIEW_EFFECTIVE_MIN_SCORE_KEY)
