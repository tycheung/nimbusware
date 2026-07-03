from __future__ import annotations

from typing import Any

FIT_COPY = {
    "perfect": "Runs fully on GPU with headroom",
    "good": "Comfortable fit for this machine",
    "marginal": "May work; expect slower runs or tight memory",
    "too_tight": "Not recommended — pick a smaller model or upgrade RAM",
}


def fit_level_caption(fit_level: str) -> str:
    return FIT_COPY.get(str(fit_level).strip().lower(), fit_level)


def pick_recommended_model(ranked: list[dict[str, Any]]) -> str | None:
    if not ranked:
        return None
    for level in ("perfect", "good", "marginal"):
        for row in ranked:
            if row.get("fit_level") == level and row.get("model_id"):
                return str(row["model_id"])
    first = ranked[0]
    mid = first.get("model_id")
    return str(mid) if mid else None


def model_options_for_select(ranked: list[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in ranked:
        mid = str(row.get("model_id") or "").strip()
        if not mid:
            continue
        fit = str(row.get("fit_level") or "")
        out.append((f"{mid} ({fit})", mid))
    return out
