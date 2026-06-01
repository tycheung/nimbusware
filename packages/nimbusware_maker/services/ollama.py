from __future__ import annotations

from typing import Any
from urllib.parse import quote

from nimbusware_client.http import delete_response, patch_response, post_json
from nimbusware_maker.api_client import get_json


def list_models(*, query: str = "") -> dict[str, Any]:
    path = "/platform/ollama/models"
    if query.strip():
        path = f"{path}?q={quote(query.strip())}"
    return get_json(path)


def pull_model(model: str) -> dict[str, Any]:
    return post_json("/platform/ollama/pull", {"model": model.strip()}, timeout=600.0)


def delete_model(model_name: str) -> None:
    delete_response(
        f"/platform/ollama/models/{quote(model_name.strip(), safe='')}",
        timeout=120.0,
    )


def set_primary_routing(primary_model_id: str) -> None:
    patch_response(
        "/platform/ollama/routing/primary",
        {"primary_model_id": primary_model_id.strip()},
        timeout=30.0,
    )
