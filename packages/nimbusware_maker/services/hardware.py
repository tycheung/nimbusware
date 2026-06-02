from __future__ import annotations

from typing import Any

from nimbusware_maker.api_client import get_json, post_json


def fetch_hardware() -> dict[str, Any]:
    return get_json("/platform/hardware")


def rescan_hardware() -> dict[str, Any]:
    return post_json("/platform/hardware/rescan", {})
