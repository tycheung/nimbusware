from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
from orchestrator.pipeline import make_dev_orchestrator


def test_integrator_gate_includes_live_context_from_adapter_writer_stage() -> None:
    orch, mem = make_dev_orchestrator()
    run_id = orch.create_run("integrator_gate_on")
    mem.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integration_adapter_writer": {
                    "target_adapter_kind": "api_bridge",
                    "target_integration_status": "integrated",
                    "target_connected": True,
                    "http_probe": {
                        "reachable": True,
                        "status_code": 200,
                        "ok": True,
                        "content_type": "application/json",
                        "body_preview": '{"status":"ok"}',
                        "attempts": 1,
                    },
                },
            },
            payload=StageStartedPayload(
                stage_name="integration_adapter_writer",
                attempt=1,
            ),
        ),
    )
    with patch(
        "orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=True,
    ):
        orch._emit_bundle_integrator_gate(run_id)  # noqa: SLF001
    gate_rows = [
        r
        for r in mem.list_run_events(str(run_id))
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
    ]
    assert gate_rows
    live_ctx = (gate_rows[-1].get("metadata") or {}).get("integrator_live_context") or {}
    assert live_ctx.get("target_adapter_kind") == "api_bridge"
    assert live_ctx.get("adapter_integration_status") == "integrated"
    assert live_ctx.get("http_probe", {}).get("status_code") == 200
