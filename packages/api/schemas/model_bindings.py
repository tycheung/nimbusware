from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RoleBindingBlock(BaseModel):
    provider_kind: str = "local"
    provider_id: str = "ollama"
    model_id: str = ""
    base_url: str | None = None
    api_key_ref: str | None = None
    connection_id: str | None = None


class UserDefaultsBody(BaseModel):
    version: int = 1
    roles: dict[str, RoleBindingBlock | dict[str, Any]] = Field(default_factory=dict)
