from __future__ import annotations

from typing import Any

from nimbusware_client.http import admin_headers, patch_response


def patch_custom_agent(agent_id: str, payload: dict[str, Any], *, timeout: float = 15.0) -> None:
    patch_response(
        f"/custom-agents/{agent_id}",
        payload,
        headers=admin_headers(),
        timeout=timeout,
    )
