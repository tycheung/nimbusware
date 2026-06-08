from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_orchestrator.context_compaction import maybe_emit_compaction_event

router = APIRouter()


class CompactRunBody(BaseModel):
    scope: Literal["all", "last_n"] = "all"
    n: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def _require_n_for_last_n(self) -> CompactRunBody:
        if self.scope == "last_n" and self.n is None:
            msg = "n is required when scope is last_n"
            raise ValueError(msg)
        return self


class CompactRunResponse(BaseModel):
    run_id: str
    compacted: bool
    summary: str | None = None
    tokens_before: int | None = None
    tokens_after: int | None = None
    kept_event_seq_range: list[int] = Field(default_factory=list)


def agent_compact_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_AGENT_COMPACT", default=True)


@router.post(
    "/runs/{run_id}/compact",
    response_model=CompactRunResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def compact_run(
    run_id: UUID,
    store: StoreDep,
    body: CompactRunBody | None = None,
) -> CompactRunResponse:
    if not agent_compact_enabled():
        raise HTTPException(
            status_code=403,
            detail=problem(
                "compact_disabled",
                "manual compaction disabled (NIMBUSWARE_AGENT_COMPACT=0)",
            ),
        )
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    scope = body.scope if body is not None else "all"
    scope_n = body.n if body is not None else None
    result = maybe_emit_compaction_event(
        store,
        run_id=run_id,
        events=rows,
        compaction_trigger="manual",
        scope=scope,
        scope_n=scope_n,
    )
    if result is None:
        return CompactRunResponse(run_id=str(run_id), compacted=False)
    kept = list(result.kept_event_seq_range)
    return CompactRunResponse(
        run_id=str(run_id),
        compacted=True,
        summary=result.summary,
        tokens_before=result.tokens_before,
        tokens_after=result.tokens_after,
        kept_event_seq_range=kept,
    )
