from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from hw.catalog import load_model_catalog
from hw.ollama_presets import ollama_presets_for_model
from hw.profile import HardwareProfile

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


def _params_hint(model_id: str, catalog: list[dict[str, Any]]) -> float:
    for row in catalog:
        if str(row.get("id")) == model_id:
            raw = row.get("params_b")
            if isinstance(raw, (int, float)):
                return float(raw)
    mid = model_id.lower()
    if "70b" in mid:
        return 70.0
    if "14b" in mid or "13b" in mid:
        return 14.0
    if "8b" in mid or "7b" in mid:
        return 8.0
    if "3b" in mid:
        return 3.0
    return 4.0


def _fit_level_for_model(
    model_id: str,
    profile: HardwareProfile,
    *,
    params_b: float,
    gpu_only: bool,
) -> str:
    tier = profile.tier
    avail = profile.ram_available_gb or profile.ram_total_gb or 8.0
    has_gpu = bool(profile.gpus) or profile.unified_memory
    size_hint = max(2.0, params_b * 0.5)
    if gpu_only and not has_gpu:
        return "too_tight"
    if gpu_only and tier == "weak":
        return "too_tight" if size_hint > 3 else "marginal"
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
    gpu_only: bool = False,
    gpu_group_index: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    del use_case
    group_gpus: list[str] = []
    if profile.gpu_groups and 0 <= gpu_group_index < len(profile.gpu_groups):
        group_gpus = list(profile.gpu_groups[gpu_group_index])
    catalog = load_model_catalog(repo_root)
    allowlist = _load_routing_models(repo_root)
    tags = installed_tags or []
    candidates = list(dict.fromkeys([*allowlist, *tags]))
    ranked: list[dict[str, Any]] = []
    for model_id in candidates:
        params_b = _params_hint(model_id, catalog)
        fit_level = _fit_level_for_model(
            model_id,
            profile,
            params_b=params_b,
            gpu_only=gpu_only,
        )
        score = {"perfect": 4, "good": 3, "marginal": 2, "too_tight": 1}[fit_level]
        row = {
            "model_id": model_id,
            "ollama_tag": model_id,
            "fit_level": fit_level,
            "score": score,
            "run_mode": (
                "gpu" if profile.tier != "weak" and (group_gpus or profile.gpus) else "cpu_only"
            ),
            "gpu_group_index": gpu_group_index,
            "required_gb": round(params_b * 0.6, 1),
            "params_b": params_b,
        }
        row["presets"] = ollama_presets_for_model(row, profile)
        ranked.append(row)
    ranked.sort(key=lambda r: (-int(r["score"]), r["model_id"]))
    if gpu_only:
        ranked = [r for r in ranked if r["fit_level"] != "too_tight"] + [
            r for r in ranked if r["fit_level"] == "too_tight"
        ]
    return ranked[: max(1, limit)]
