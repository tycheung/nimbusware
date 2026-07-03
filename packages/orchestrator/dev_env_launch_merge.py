from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def dev_env_live_regression_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    http: bool | None = None
    ui: bool | None = None
    http_detail = ""
    ui_detail = ""
    ui_flow_id = ""
    failed_step: int | None = None
    failed_locator = ""
    slice_e2e: bool | None = None
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
        if isinstance(block, dict):
            if stage.startswith("dev_env.regression") and http is None:
                http = stage.endswith(".passed")
                http_detail = str(block.get("regression") or block.get("detail") or "")[:500]
            if stage.startswith("dev_env.ui_regression") and ui is None:
                ui = stage.endswith(".passed")
                ui_detail = str(block.get("ui_regression") or block.get("detail") or "")[:500]
                ui_flow_id = str(block.get("flow_id") or "")
                raw_step = block.get("failed_step")
                if raw_step is not None:
                    failed_step = int(raw_step)
                failed_locator = str(block.get("locator") or "")
        if stage.startswith("slice.e2e") and slice_e2e is None:
            slice_e2e = stage.endswith(".passed") or et == EventType.STAGE_PASSED.value
        if http is not None and ui is not None and slice_e2e is not None:
            break
    out: dict[str, Any] = {}
    if http is not None:
        out["dev_env_http_regression_passed"] = http
        if http_detail:
            out["dev_env_http_regression_detail"] = http_detail
    if ui is not None:
        out["dev_env_ui_regression_passed"] = ui
        out["put_ui_flow_passed"] = ui
        if ui_detail:
            out["dev_env_ui_regression_detail"] = ui_detail
        if ui_flow_id:
            out["put_ui_flow_id"] = ui_flow_id
        if failed_step is not None:
            out["dev_env_ui_failed_step"] = failed_step
        if failed_locator:
            out["dev_env_ui_failed_locator"] = failed_locator
    if slice_e2e is not None:
        out["slice_e2e_passed"] = slice_e2e
    if http is not None or ui is not None:
        out["dev_env_live_regression_passed"] = (http is not False) and (ui is not False)
    return out
