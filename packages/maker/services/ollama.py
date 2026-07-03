from __future__ import annotations

from typing import Any

from client.http import delete_response, patch_response, post_json
from client.ollama_paths import ollama_model_delete_path, ollama_models_path
from maker.api_client import get_json


def list_models(*, query: str = "") -> dict[str, Any]:
    return get_json(ollama_models_path(query=query))


def pull_model(model: str) -> dict[str, Any]:
    return post_json("/platform/ollama/pull", {"model": model.strip()}, timeout=600.0)


def delete_model(model_name: str) -> None:
    delete_response(
        ollama_model_delete_path(model_name),
        timeout=120.0,
    )


def set_primary_routing(primary_model_id: str) -> None:
    patch_response(
        "/platform/ollama/routing/primary",
        {"primary_model_id": primary_model_id.strip()},
        timeout=30.0,
    )
