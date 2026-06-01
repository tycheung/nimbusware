from __future__ import annotations

from typing import Any

from nimbusware_maker.api_client import get_json, post_json


def list_projects() -> dict[str, Any]:
    return get_json("/projects")


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    return post_json("/projects", payload)
