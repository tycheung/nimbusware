from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchBriefSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(min_length=1, max_length=2048)
    license: str = Field(min_length=1, max_length=64)
    trust_tier: Literal["high", "medium", "low"] = "medium"


class ResearchBrief(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    brief_kind: Literal["domain", "code"]
    domain_tag: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=8000)
    artifact_id: str = Field(min_length=1, max_length=128)
    sources: tuple[ResearchBriefSource, ...] = ()
