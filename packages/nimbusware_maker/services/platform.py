from __future__ import annotations

from typing import Any

from nimbusware_maker.api_client import get_json


def fetch_readiness() -> dict[str, Any]:
    return get_json("/platform/readiness")
