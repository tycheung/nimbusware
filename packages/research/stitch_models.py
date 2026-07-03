from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransplantManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_id: str = Field(min_length=1, max_length=128)
    source_kind: Literal["oss", "bundle", "stub"]
    source_tree_hash: str = Field(min_length=8, max_length=64)
    file_paths: tuple[str, ...] = ()
    license_paths: tuple[str, ...] = ()
    required_env_vars: tuple[str, ...] = ()
