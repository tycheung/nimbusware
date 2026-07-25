from __future__ import annotations

from typing import Any

from maker.api_client import get_json, post_json


def is_capacity_miss(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    if body.get("via") == "broker_miss":
        return True
    if body.get("capacity_source") == "broker_miss":
        return True
    return False


def assert_capacity_ok(body: Any, *, feature: str) -> dict[str, Any]:
    """Raise when ranked/apply/hardware body is a peel miss (`sak444-g`)."""
    if not isinstance(body, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {body!r}")
    if is_capacity_miss(body):
        raise RuntimeError(
            f"broker_miss: {feature}: {body.get('error') or body.get('feature') or 'miss'}"
        )
    if body.get("error") is not None and "models" not in body and "profile" not in body:
        raise RuntimeError(f"broker_miss: {feature}: {body.get('error')!r}")
    return body


def fetch_models_ranked(
    *,
    use_case: str = "coding",
    gpu_only: bool = False,
    gpu_group_index: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    raw = get_json(
        "/platform/models/ranked",
        params={
            "use_case": use_case,
            "gpu_only": gpu_only,
            "gpu_group_index": gpu_group_index,
            "limit": limit,
        },
    )
    return assert_capacity_ok(raw, feature="platform_models_ranked")


def fetch_model_dependencies() -> dict[str, Any]:
    raw = get_json("/platform/models/dependencies")
    return assert_capacity_ok(raw, feature="platform_models_dependencies")


def apply_model_preset(
    *,
    model_id: str,
    preset: str = "balanced",
) -> dict[str, Any]:
    raw = post_json(
        "/platform/models/apply-preset",
        {"model_id": model_id, "preset": preset, "target": "model-routing"},
    )
    return assert_capacity_ok(raw, feature="platform_models_apply_preset")
