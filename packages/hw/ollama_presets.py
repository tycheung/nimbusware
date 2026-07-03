from __future__ import annotations

from typing import Any

from hw.profile import HardwareProfile

PRESET_NAMES = ("quality", "balanced", "speed")


def ollama_presets_for_model(
    model_row: dict[str, Any],
    profile: HardwareProfile,
) -> dict[str, dict[str, Any]]:
    model_id = str(model_row.get("model_id") or "")
    fit = str(model_row.get("fit_level") or "marginal")
    ctx_cap = 32768 if profile.tier == "strong" else 8192 if profile.tier == "medium" else 4096
    return {
        "quality": {
            "ollama_tag": model_id,
            "num_ctx": ctx_cap,
            "note": "Largest comfortable quant; full context when fit allows",
        },
        "balanced": {
            "ollama_tag": model_id,
            "num_ctx": min(ctx_cap, 8192),
            "note": "Default routing profile",
        },
        "speed": {
            "ollama_tag": model_id,
            "num_ctx": min(4096, ctx_cap),
            "note": "Reduced context for faster iteration" if fit != "too_tight" else "Tight fit",
        },
    }
