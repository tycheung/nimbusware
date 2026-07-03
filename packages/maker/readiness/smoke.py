from __future__ import annotations

from typing import Any


def readiness_smoke_ok(payload: dict[str, Any]) -> tuple[bool, str]:
    status = str(payload.get("status") or "").strip().lower()
    if status in ("ready", "degraded"):
        return True, ""
    if status == "not_ready":
        return (
            False,
            "Platform is not ready. Fix the checks above or follow the install guide.",
        )
    return False, f"Unexpected readiness status: {status or 'unknown'}"
