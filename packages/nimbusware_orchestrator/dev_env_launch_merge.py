from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def dev_env_live_regression_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Latest HTTP/UI regression outcome from run events (for launch eval merge)."""
    http: bool | None = None
    ui: bool | None = None
    http_detail = ""
    ui_detail = ""
    for row in reversed(rows):
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "")
        et = str(row.get("event_type") or "")
        if et not in {EventType.STAGE_PASSED.value, EventType.STAGE_STARTED.value}:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        block = meta.get("dev_env")
        if not isinstance(block, dict):
            continue
        if stage.startswith("dev_env.regression") and http is None:
            http = stage.endswith(".passed")
            http_detail = str(block.get("regression") or block.get("detail") or "")[:500]
        if stage.startswith("dev_env.ui_regression") and ui is None:
            ui = stage.endswith(".passed")
            ui_detail = str(block.get("regression") or block.get("detail") or "")[:500]
        if http is not None and ui is not None:
            break
    out: dict[str, Any] = {}
    if http is not None:
        out["dev_env_http_regression_passed"] = http
        if http_detail:
            out["dev_env_http_regression_detail"] = http_detail
    if ui is not None:
        out["dev_env_ui_regression_passed"] = ui
        if ui_detail:
            out["dev_env_ui_regression_detail"] = ui_detail
    if http is not None or ui is not None:
        out["dev_env_live_regression_passed"] = (http is not False) and (ui is not False)
    return out
