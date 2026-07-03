from __future__ import annotations

from typing import Any

from maker.api_client import get_json


def fetch_run_theater(run_id: str, *, cursor: int = 0, limit: int = 50) -> dict[str, Any]:
    return get_json(
        f"/runs/{run_id}/theater",
        params={"cursor": cursor, "limit": limit},
    )
