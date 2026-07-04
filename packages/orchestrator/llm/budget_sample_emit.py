from __future__ import annotations

import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    ContextBudgetSampledEvent,
    ContextBudgetSampledPayload,
    EventType,
)
from store.protocol import EventStore

_store_ctx: ContextVar[EventStore | None] = ContextVar("budget_sample_store", default=None)
_run_id_ctx: ContextVar[UUID | None] = ContextVar("budget_sample_run_id", default=None)
_last_emit_monotonic: dict[str, float] = {}
_EMIT_INTERVAL_S = 30.0


def bind_budget_sample_context(*, store: EventStore, run_id: UUID) -> None:
    _store_ctx.set(store)
    _run_id_ctx.set(run_id)


def clear_budget_sample_context() -> None:
    _store_ctx.set(None)
    _run_id_ctx.set(None)


def maybe_emit_context_budget_sample(
    *,
    provider: str,
    stage_name: str,
    tokens_in: int,
    tokens_out: int,
    cache_read: int = 0,
    cache_write: int = 0,
) -> None:
    store = _store_ctx.get()
    run_id = _run_id_ctx.get()
    if store is None or run_id is None:
        return
    key = str(run_id)
    now = time.monotonic()
    last = _last_emit_monotonic.get(key, 0.0)
    if now - last < _EMIT_INTERVAL_S:
        return
    _last_emit_monotonic[key] = now
    store.append(
        ContextBudgetSampledEvent(
            event_type=EventType.CONTEXT_BUDGET_SAMPLED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ContextBudgetSampledPayload(
                provider=provider,
                stage_name=stage_name,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cache_read=cache_read,
                cache_write=cache_write,
            ),
        ),
    )
