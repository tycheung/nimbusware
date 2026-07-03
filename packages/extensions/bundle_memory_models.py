from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BundleOutcomeRecord(BaseModel):
    model_config = {"frozen": True}

    outcome_id: UUID
    run_id: UUID
    bundle_id: str
    workflow_profile: str | None = None
    project_tags: tuple[str, ...] = ()
    integrator_score: float | None = None
    verdict: str
    source_store_seq: int | None = None
    recorded_at: datetime | None = None


class BundleSuccessStats(BaseModel):
    model_config = {"frozen": True}

    bundle_id: str
    pass_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    sample_count: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    last_verdict: str | None = None
    avg_integrator_score: float | None = None
    avg_score_on_pass: float | None = None
    avg_score_on_fail: float | None = None
