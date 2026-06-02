from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_hw.profile import HardwareProfile

FIT_LEVELS = ("perfect", "good", "marginal", "too_tight")


def _load_routing_models(repo_root: Path) -> list[str]:
    path = repo_root / "configs" / "model-routing.yaml"
    if not path.is_file():
        return []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    models_raw = doc.get("models")
    if not isinstance(models_raw, dict):
        return []
    out: list[str] = []
    primary = models_raw.get("primary")
    if isinstance(primary, dict):
        pid = primary.get("id")
        if isinstance(pid, str) and pid.strip():
            out.append(pid.strip())
    fallbacks = models_raw.get("fallbacks")
    if isinstance(fallbacks, list):
        for fb in fallbacks:
            if isinstance(fb, dict):
                fid = fb.get("id")
                if isinstance(fid, str) and fid.strip():
                    out.append(fid.strip())
    return out


def _fit_level_for_model(model_id: str, profile: HardwareProfile) -> str:
    tier = profile.tier
    size_hint = 8 if "70b" in model_id.lower() else 4 if "14b" in model_id.lower() else 2
    avail = profile.ram_available_gb or profile.ram_total_gb or 8.0
    if tier == "strong" and avail >= size_hint + 4:
        return "perfect"
    if tier == "medium" and avail >= size_hint + 2:
        return "good"
    if avail >= size_hint:
        return "marginal"
    return "too_tight"


def rank_models(
    repo_root: Path,
    profile: HardwareProfile,
    *,
    installed_tags: list[str] | None = None,
    use_case: str = "coding",
) -> list[dict[str, Any]]:
    del use_case
    allowlist = _load_routing_models(repo_root)
    tags = installed_tags or []
    candidates = list(dict.fromkeys([*allowlist, *tags]))
    ranked: list[dict[str, Any]] = []
    for model_id in candidates:
        fit_level = _fit_level_for_model(model_id, profile)
        score = {"perfect": 4, "good": 3, "marginal": 2, "too_tight": 1}[fit_level]
        ranked.append(
            {
                "model_id": model_id,
                "fit_level": fit_level,
                "score": score,
                "run_mode": "gpu" if profile.tier != "weak" else "cpu",
                "required_gb": 4.0,
            },
        )
    ranked.sort(key=lambda r: (-int(r["score"]), r["model_id"]))
    return ranked
