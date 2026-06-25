from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParticipantOutputPacket(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    agent_role: str = Field(min_length=1, max_length=128)
    stage: str = Field(min_length=1, max_length=128)
    model_id: str = Field(default="", max_length=256)
    provider_id: str = Field(default="", max_length=128)
    verdict: str = Field(default="", max_length=32)
    summary: str = Field(default="", max_length=4000)
    diff_excerpt: str = Field(default="", max_length=8000)
    test_log_excerpt: str = Field(default="", max_length=8000)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    full_output: str = Field(default="", max_length=16000)

    def to_wire_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
