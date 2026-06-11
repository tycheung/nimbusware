from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("metadata")
    return mapping_or_empty(meta)


def _latest_put_e2e(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in events:
        meta = _metadata(row)
        block = meta.get("put_e2e")
        if isinstance(block, dict):
            latest = block
    return latest


def _latest_factory_block(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in events:
        meta = _metadata(row)
        block = meta.get("factory")
        if isinstance(block, dict):
            latest = block
    return latest


def factory_status_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    factory_block = _latest_factory_block(events)
    put_e2e = _latest_put_e2e(events)

    tier_raw = None
    ism_coverage: float | None = None
    put_e2e_passed: bool | None = None

    if factory_block:
        tier_raw = factory_block.get("tier")
        raw_cov = factory_block.get("ism_coverage_pct")
        if isinstance(raw_cov, (int, float)):
            ism_coverage = float(raw_cov)
        passed = factory_block.get("put_e2e_passed")
        if isinstance(passed, bool):
            put_e2e_passed = passed

    if put_e2e:
        verdict = str(put_e2e.get("verdict") or "").upper()
        if put_e2e_passed is None:
            if verdict == "PASS":
                put_e2e_passed = True
            elif verdict == "FAIL":
                put_e2e_passed = False
        raw_cov = put_e2e.get("ism_coverage_pct")
        if ism_coverage is None and isinstance(raw_cov, (int, float)):
            ism_coverage = float(raw_cov)
        if tier_raw is None:
            tier_raw = put_e2e.get("tier")

    if tier_raw is None and put_e2e_passed is None and ism_coverage is None:
        return None

    tier = "T1"
    token = str(tier_raw or "").strip().upper()
    if token in {"T0", "T1", "T2", "T3"}:
        tier = token
    return {
        "tier": tier,
        "ism_coverage_pct": ism_coverage if ism_coverage is not None else 0.0,
        "put_e2e_passed": put_e2e_passed,
    }
