from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from nimbusware_orchestrator.dev_env_session import DevEnvironmentSession


def _dev_env_metadata(session: DevEnvironmentSession, **extra: Any) -> dict[str, Any]:
    block = {
        "session_id": session.session_id,
        "base_url": session.base_url,
        "stack": session.stack,
        "port": session.port,
        "attach_mode": session.attach_mode,
        "adapter": session.adapter,
        "health": session.health,
    }
    block.update(extra)
    return {"dev_env": block}


def emit_dev_env_started(store: Any, run_id: UUID | str, session: DevEnvironmentSession) -> None:
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=_dev_env_metadata(session),
            payload=StageStartedPayload(stage_name="dev_env.started", attempt=1),
        ),
    )


def emit_dev_env_stopped(store: Any, run_id: UUID | str, session: DevEnvironmentSession) -> None:
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=_dev_env_metadata(session, health="stopped"),
            payload=StageStartedPayload(stage_name="dev_env.stopped", attempt=1),
        ),
    )


def emit_dev_env_health(
    store: Any,
    run_id: UUID | str,
    session: DevEnvironmentSession,
    *,
    degraded: bool = False,
) -> None:
    stage = "dev_env.health.degraded" if degraded else "dev_env.health.ok"
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=_dev_env_metadata(session),
            payload=StagePassedPayload(stage_name=stage, attempt=1),
        ),
    )


def emit_dev_env_regression(
    store: Any,
    run_id: UUID | str,
    *,
    passed: bool,
    detail: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    stage = "dev_env.regression.passed" if passed else "dev_env.regression.failed"
    event_cls = StagePassedEvent if passed else StageStartedEvent
    payload_cls = StagePassedPayload if passed else StageStartedPayload
    store.append(
        event_cls(
            event_type=EventType.STAGE_PASSED if passed else EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"dev_env": {"regression": detail, **(metadata or {})}},
            payload=payload_cls(stage_name=stage, attempt=1),
        ),
    )


def emit_dev_env_ui_regression(
    store: Any,
    run_id: UUID | str,
    *,
    passed: bool,
    steps_run: int,
    detail: str,
) -> None:
    stage = "dev_env.ui_regression.passed" if passed else "dev_env.ui_regression.failed"
    event_cls = StagePassedEvent if passed else StageStartedEvent
    payload_cls = StagePassedPayload if passed else StageStartedPayload
    store.append(
        event_cls(
            event_type=EventType.STAGE_PASSED if passed else EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "dev_env": {
                    "ui_regression": detail,
                    "steps_run": steps_run,
                }
            },
            payload=payload_cls(stage_name=stage, attempt=1),
        ),
    )
