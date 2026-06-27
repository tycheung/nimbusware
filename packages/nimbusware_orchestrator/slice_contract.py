from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SliceContractResult:
    passed: bool
    detail: str


def run_slice_contract_check(
    workspace: Path,
    *,
    require_openapi: bool = True,
) -> SliceContractResult:
    ws = workspace.resolve()
    candidates = [
        ws / "openapi.yaml",
        ws / "openapi.json",
        ws / "backend" / "openapi.yaml",
        ws / "backend" / "openapi.json",
        ws / "shared" / "openapi.yaml",
        ws / "contracts" / "openapi.yaml",
    ]
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return SliceContractResult(passed=True, detail=f"contract artifact: {path.name}")
    if not require_openapi:
        return SliceContractResult(passed=True, detail="contract check skipped")
    return SliceContractResult(
        passed=False,
        detail="missing OpenAPI or shared schema artifact for api/web contract gate",
    )
