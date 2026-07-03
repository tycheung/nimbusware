from __future__ import annotations

from typing import Any

from maker.api_client import get_json, post_json


def fetch_models_ranked(
    *,
    use_case: str = "coding",
    gpu_only: bool = False,
    gpu_group_index: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    return get_json(
        "/platform/models/ranked",
        params={
            "use_case": use_case,
            "gpu_only": gpu_only,
            "gpu_group_index": gpu_group_index,
            "limit": limit,
        },
    )


def fetch_model_dependencies() -> dict[str, Any]:
    return get_json("/platform/models/dependencies")


def apply_model_preset(
    *,
    model_id: str,
    preset: str = "balanced",
) -> dict[str, Any]:
    return post_json(
        "/platform/models/apply-preset",
        {"model_id": model_id, "preset": preset, "target": "model-routing"},
    )
