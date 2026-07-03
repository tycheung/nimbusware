from __future__ import annotations

from typing import Any

from maker.api_client import get_json, patch_json


def fetch_user_settings() -> dict[str, Any]:
    return get_json("/settings/me")


def patch_user_settings(values: dict[str, str]) -> dict[str, Any]:
    return patch_json("/settings/me", {"values": values})
