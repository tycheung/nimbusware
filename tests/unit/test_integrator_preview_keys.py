from __future__ import annotations

from nimbusware_console.integrator_threshold_explainer.keys import (
    LEGACY_PREVIEW_EFFECTIVE_MIN_SCORE_KEY,
    get_preview_effective_min_score,
)


def test_legacy_streamlit_preview_key_alias() -> None:
    payload = {LEGACY_PREVIEW_EFFECTIVE_MIN_SCORE_KEY: 0.42}
    assert get_preview_effective_min_score(payload) == 0.42
