from __future__ import annotations

from maker.wizard_model import (
    fit_level_caption,
    model_options_for_select,
    pick_recommended_model,
)


def test_pick_recommended_model_prefers_good_fit() -> None:
    ranked = [
        {"model_id": "huge", "fit_level": "too_tight", "score": 1},
        {"model_id": "small", "fit_level": "good", "score": 3},
    ]
    assert pick_recommended_model(ranked) == "small"


def test_fit_level_caption() -> None:
    assert "headroom" in fit_level_caption("perfect")


def test_model_options_for_select() -> None:
    opts = model_options_for_select([{"model_id": "llama3", "fit_level": "good"}])
    assert opts[0][1] == "llama3"
