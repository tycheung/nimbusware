from __future__ import annotations

from typing import Any

from maker.api_client import get_json, post_json


def list_projects() -> dict[str, Any]:
    return get_json("/projects")


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    return post_json("/projects", payload)


def update_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from maker.api_client import patch_json

    return patch_json(f"/projects/{project_id}", payload)
