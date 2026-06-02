from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GpuInfo(BaseModel):
    name: str = ""
    vram_gb: float | None = None
    backend: str | None = None


class HardwareProfile(BaseModel):
    tier: str = Field(description="weak | medium | strong")
    ram_total_gb: float | None = None
    ram_available_gb: float | None = None
    cpu_count: int = 1
    gpus: list[GpuInfo] = Field(default_factory=list)
    gpu_groups: list[list[str]] = Field(default_factory=list)
    unified_memory: bool = False
    errors: list[str] = Field(default_factory=list)
    platform: str = ""

    def model_dump_public(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def profile_from_probe(raw: dict[str, Any]) -> HardwareProfile:
    gpus_raw = raw.get("gpus") or []
    gpus: list[GpuInfo] = []
    if isinstance(gpus_raw, list):
        for item in gpus_raw:
            if isinstance(item, dict):
                gpus.append(GpuInfo.model_validate(item))
    groups_raw = raw.get("gpu_groups") or []
    groups: list[list[str]] = []
    if isinstance(groups_raw, list):
        for g in groups_raw:
            if isinstance(g, list):
                groups.append([str(x) for x in g])
    return HardwareProfile(
        tier=str(raw.get("tier") or "weak"),
        ram_total_gb=raw.get("ram_total_gb"),
        ram_available_gb=raw.get("ram_available_gb"),
        cpu_count=int(raw.get("cpu_count") or 1),
        gpus=gpus,
        gpu_groups=groups,
        unified_memory=bool(raw.get("unified_memory")),
        errors=[str(e) for e in raw.get("errors") or [] if str(e)],
        platform=str(raw.get("platform") or ""),
    )
