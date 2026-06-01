from __future__ import annotations

from pydantic import BaseModel, Field


class OllamaUserPolicyBody(BaseModel):
    allow_pull: bool = False
    allow_delete: bool = False
    allow_update_routing: bool = False


class OllamaModelEntry(BaseModel):
    name: str
    size_bytes: int | None = None
    modified_at: str | None = None
    digest: str | None = None


class OllamaModelsResponse(BaseModel):
    reachable: bool
    base_url: str
    primary_model_id: str | None = None
    fallback_model_ids: list[str] = Field(default_factory=list)
    user_policy: OllamaUserPolicyBody
    models: list[OllamaModelEntry] = Field(default_factory=list)
    query: str | None = None


class OllamaPullRequest(BaseModel):
    model: str = Field(..., min_length=1)


class OllamaPullResponse(BaseModel):
    model: str
    status: str = "pulled"


class OllamaDeleteResponse(BaseModel):
    model: str
    status: str = "deleted"


class OllamaPrimaryRoutingRequest(BaseModel):
    primary_model_id: str = Field(..., min_length=1)
