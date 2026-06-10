"""Factory tier gates (T0–T3) and PUT E2E fix backlog slices."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from agent_core.mapping import mapping_or_empty
from agent_core.models.backlog import (
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.interaction_surface_map import InteractionSurfaceMap, coverage_pct
from nimbusware_orchestrator.put_e2e_runner import PutE2EFinding, PutE2EResult

FactoryTier = Literal["T0", "T1", "T2", "T3"]
PUT_E2E_FIX_CATEGORY = "put_e2e_fix"


@dataclass(frozen=True)
class FactoryGateResult:
    tier: FactoryTier
    passed: bool
    blocking: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


def factory_tier_policy_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "factory" / "factory_tier_policy.yaml"


def load_factory_tier_policy(repo_root: Path | None = None) -> dict[str, Any]:
    path = factory_tier_policy_path(repo_root)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def tier_config(tier: FactoryTier, repo_root: Path | None = None) -> dict[str, Any]:
    doc = load_factory_tier_policy(repo_root)
    tiers = mapping_or_empty(doc.get("factory_tiers"))
    block = tiers.get(tier) if isinstance(tiers, dict) else None
    return dict(block) if isinstance(block, dict) else {}


def resolve_factory_tier(
    *,
    env_tier: str | None = None,
    metadata_tier: str | None = None,
    default: FactoryTier = "T1",
) -> FactoryTier:
    for raw in (metadata_tier, env_tier):
        token = str(raw or "").strip().upper()
        if token == "T2B":
            return "T2"
        if token in {"T0", "T1", "T2", "T3"}:
            return token  # type: ignore[return-value]
    return default


def factory_ui_flow_required(*, metadata_tier: str | None = None) -> bool:
    token = str(metadata_tier or "").strip().upper()
    return token in {"T2B", "T3"}


def evaluate_factory_gates(
    tier: FactoryTier,
    *,
    put_preview_ok: bool | None = None,
    ism: InteractionSurfaceMap | None = None,
    put_e2e: PutE2EResult | None = None,
    ism_coverage_pct_value: float | None = None,
    repo_root: Path | None = None,
) -> FactoryGateResult:
    cfg = tier_config(tier, repo_root)
    blocking: list[str] = []
    details: dict[str, Any] = {
        "tier_label": cfg.get("label"),
        "put_preview_enabled": bool(cfg.get("put_preview_enabled", False)),
        "ism_discovery": cfg.get("ism_discovery"),
    }

    preview_required = bool(cfg.get("put_preview_enabled", False))
    if preview_required:
        if put_preview_ok is not True:
            blocking.append("put_preview_not_ready")
    elif put_preview_ok is False:
        blocking.append("put_preview_failed_at_t0")

    ism_mode = str(cfg.get("ism_discovery") or "stub")
    surface_count = len(ism.surfaces) if ism is not None else 0
    details["ism_surface_count"] = surface_count
    if ism_mode == "stub":
        pass
    elif ism_mode == "static":
        if surface_count < 1:
            blocking.append("ism_static_empty")
    elif ism_mode in {"openapi", "full"}:
        if surface_count < 1:
            blocking.append("ism_openapi_empty")
        elif ism is not None and ism.source not in {"openapi", "openapi+html", "full"}:
            if ism_mode == "openapi" and ism.source == "html":
                blocking.append("ism_missing_openapi")

    coverage = ism_coverage_pct_value
    if coverage is None and ism is not None and put_e2e is not None:
        coverage = coverage_pct(ism, put_e2e.exercised_paths)
    if coverage is not None:
        details["ism_coverage_pct"] = coverage

    if tier in {"T2", "T3"}:
        if put_e2e is None:
            blocking.append("put_e2e_not_run")
        elif put_e2e.verdict == "SKIP":
            blocking.append("put_e2e_skipped")
        elif put_e2e.verdict != "PASS":
            blocking.append("put_e2e_failed")

    if tier == "T3":
        min_coverage = 50.0
        if coverage is None or coverage < min_coverage:
            blocking.append("ism_coverage_below_t3_threshold")
        details["t3_min_coverage_pct"] = min_coverage

    return FactoryGateResult(
        tier=tier,
        passed=not blocking,
        blocking=tuple(blocking),
        details=details,
    )


def put_e2e_fix_slice_id(*, index: int = 1) -> str:
    return f"put-e2e-fix-{index:03d}"


def build_put_e2e_fix_slice(
    findings: list[PutE2EFinding] | list[dict[str, Any]],
    *,
    flow_id: str = "",
    depends_on: tuple[str, ...] = (),
) -> BacklogSlice:
    messages: list[str] = []
    for item in findings:
        if isinstance(item, PutE2EFinding):
            messages.append(item.message)
        elif isinstance(item, dict):
            messages.append(str(item.get("message") or item.get("kind") or "finding"))
    summary = "; ".join(messages[:3]) if messages else "PUT E2E flow failed"
    rationale = f"[{PUT_E2E_FIX_CATEGORY}] {summary[:400]}"
    if flow_id:
        rationale = f"[{PUT_E2E_FIX_CATEGORY}:{flow_id}] {summary[:380]}"
    return BacklogSlice(
        slice_id=put_e2e_fix_slice_id(),
        status=SliceStatus.PENDING,
        target_paths=("packages/nimbusware_orchestrator/put_e2e_runner.py",),
        depends_on=depends_on,
        estimated_loc=60,
        rationale=rationale,
    )


def append_put_e2e_fix_slice(
    backlog: DeliveryBacklog,
    findings: list[PutE2EFinding] | list[dict[str, Any]],
    *,
    flow_id: str = "",
) -> DeliveryBacklog:
    if not backlog.epics:
        return backlog
    epic = backlog.epics[0]
    if not epic.features:
        return backlog
    feature = epic.features[0]
    existing_ids = {s.slice_id for s in feature.slices}
    fix_slice = build_put_e2e_fix_slice(findings, flow_id=flow_id)
    if fix_slice.slice_id in existing_ids:
        return backlog
    new_slices = tuple(feature.slices) + (fix_slice,)
    new_feature = feature.model_copy(update={"slices": new_slices})
    new_features = (new_feature,) + epic.features[1:]
    new_epic = epic.model_copy(update={"features": new_features, "status": EpicStatus.IN_PROGRESS})
    new_epics = (new_epic,) + backlog.epics[1:]
    revised = backlog.model_copy(update={"epics": new_epics})
    return sync_backlog_metadata(revised)


def handle_put_e2e_failure(
    backlog: DeliveryBacklog | None,
    put_e2e: PutE2EResult,
) -> DeliveryBacklog | None:
    if put_e2e.verdict != "FAIL":
        return backlog
    if backlog is None:
        return None
    return append_put_e2e_fix_slice(
        backlog,
        put_e2e.findings,
        flow_id=put_e2e.flow_id,
    )
