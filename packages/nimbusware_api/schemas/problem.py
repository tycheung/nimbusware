"""RFC7807-style problem body for OpenAPI (matches ``nimbusware_api.errors.problem``)."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
class Problem(BaseModel):
    """Flat JSON error envelope for ``/v1`` (``code`` + ``message`` + optional ``details``)."""
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: dict[str, Any] | None = Field(default=None)
