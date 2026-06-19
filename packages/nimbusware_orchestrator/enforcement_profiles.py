from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import yaml

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from nimbusware_env import find_repo_root

ENFORCEMENT_UPDATED_STAGE = "run.enforcement.updated"

RuffScope = Literal["off", "scoped", "workspace"]
TestsMode = Literal["skip_ok", "mapped_required", "full", "full_with_coverage"]
SecurityMode = Literal["off", "ruff", "bandit", "full_scan"]
PipAuditMode = Literal["off", "if_lockfile", "required"]
E2eMode = Literal["skip_ok", "if_present", "required"]
SkipVerdictPolicy = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class EnforcementProfile:
    level: int
    name: str
    ruff_scope: RuffScope = "scoped"
    ruff_format_check: bool = False
    tests_mode: TestsMode = "skip_ok"
    coverage_floor: float | None = None
    security_mode: SecurityMode = "off"
    pip_audit: PipAuditMode = "off"
    e2e_mode: E2eMode = "skip_ok"
    universal_critique: bool = False
    fast_slice_allowed: bool = True
    skip_verdict_policy: SkipVerdictPolicy = "pass"
    milestone_full_ci: bool = False
    terminal_parity_ci: bool = False
    custom: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "name": self.name,
            "ruff_scope": self.ruff_scope,
            "ruff_format_check": self.ruff_format_check,
            "tests_mode": self.tests_mode,
            "coverage_floor": self.coverage_floor,
            "security_mode": self.security_mode,
            "pip_audit": self.pip_audit,
            "e2e_mode": self.e2e_mode,
            "universal_critique": self.universal_critique,
            "fast_slice_allowed": self.fast_slice_allowed,
            "skip_verdict_policy": self.skip_verdict_policy,
            "milestone_full_ci": self.milestone_full_ci,
            "terminal_parity_ci": self.terminal_parity_ci,
            "custom": self.custom,
        }


_LEVEL_TABLE: tuple[tuple[int, str, dict[str, Any]], ...] = (
    (
        0,
        "Sketch",
        {
            "ruff_scope": "off",
            "tests_mode": "skip_ok",
            "security_mode": "off",
            "e2e_mode": "skip_ok",
            "fast_slice_allowed": True,
        },
    ),
    (
        1,
        "Lint-only",
        {
            "ruff_scope": "scoped",
            "tests_mode": "skip_ok",
            "e2e_mode": "skip_ok",
        },
    ),
    (
        2,
        "Patch-lite",
        {
            "ruff_scope": "scoped",
            "tests_mode": "skip_ok",
            "e2e_mode": "skip_ok",
        },
    ),
    (
        3,
        "Standard",
        {
            "ruff_scope": "scoped",
            "tests_mode": "skip_ok",
            "e2e_mode": "if_present",
        },
    ),
    (
        4,
        "Mapped tests",
        {
            "ruff_scope": "scoped",
            "tests_mode": "mapped_required",
            "e2e_mode": "if_present",
        },
    ),
    (
        5,
        "Balanced",
        {
            "ruff_scope": "workspace",
            "tests_mode": "mapped_required",
            "security_mode": "bandit",
            "e2e_mode": "if_present",
            "universal_critique": True,
            "skip_verdict_policy": "warn",
        },
    ),
    (
        6,
        "Strict slice",
        {
            "ruff_scope": "workspace",
            "tests_mode": "mapped_required",
            "security_mode": "bandit",
            "e2e_mode": "if_present",
            "universal_critique": True,
            "fast_slice_allowed": False,
            "skip_verdict_policy": "fail",
            "milestone_full_ci": True,
        },
    ),
    (
        7,
        "Pre-production",
        {
            "ruff_scope": "workspace",
            "ruff_format_check": True,
            "tests_mode": "full",
            "security_mode": "full_scan",
            "pip_audit": "if_lockfile",
            "e2e_mode": "required",
            "universal_critique": True,
            "fast_slice_allowed": False,
            "skip_verdict_policy": "fail",
            "milestone_full_ci": True,
        },
    ),
    (
        8,
        "Release candidate",
        {
            "ruff_scope": "workspace",
            "ruff_format_check": True,
            "tests_mode": "full_with_coverage",
            "coverage_floor": 0.75,
            "security_mode": "full_scan",
            "pip_audit": "if_lockfile",
            "e2e_mode": "required",
            "universal_critique": True,
            "fast_slice_allowed": False,
            "skip_verdict_policy": "fail",
            "milestone_full_ci": True,
        },
    ),
    (
        9,
        "Platform-grade",
        {
            "ruff_scope": "workspace",
            "ruff_format_check": True,
            "tests_mode": "full_with_coverage",
            "coverage_floor": 0.75,
            "security_mode": "full_scan",
            "pip_audit": "required",
            "e2e_mode": "required",
            "universal_critique": True,
            "fast_slice_allowed": False,
            "skip_verdict_policy": "fail",
            "milestone_full_ci": True,
            "terminal_parity_ci": True,
        },
    ),
    (
        10,
        "Nimbusware parity",
        {
            "ruff_scope": "workspace",
            "ruff_format_check": True,
            "tests_mode": "full_with_coverage",
            "coverage_floor": 0.75,
            "security_mode": "full_scan",
            "pip_audit": "required",
            "e2e_mode": "required",
            "universal_critique": True,
            "fast_slice_allowed": False,
            "skip_verdict_policy": "fail",
            "milestone_full_ci": True,
            "terminal_parity_ci": True,
        },
    ),
)


def preset_for_enforcement_level(level: int) -> EnforcementProfile:
    level = max(0, min(10, level))
    for spec_level, name, overrides in _LEVEL_TABLE:
        if spec_level == level:
            return EnforcementProfile(level=level, name=name, **overrides)
    return EnforcementProfile(level=level, name=f"Level {level}")


def default_enforcement_level_for_work_type(work_type: str | None) -> int:
    wt = str(work_type or "").strip().lower()
    if wt == "factory":
        return 7
    if wt == "patch":
        return 4
    return 5


def enforcement_effective_metadata(work_type: str | None) -> dict[str, Any]:
    level = default_enforcement_level_for_work_type(work_type)
    profile = preset_for_enforcement_level(level)
    return {
        "level": profile.level,
        "name": profile.name,
        "source": "work_type_default",
        **{k: v for k, v in profile.to_dict().items() if k not in {"level", "name", "custom"}},
    }


def presets_config_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enforcement" / "presets.yaml"


def load_enforcement_presets(repo_root: Path | None = None) -> dict[str, Any]:
    path = presets_config_path(repo_root)
    if not path.is_file():
        return {
            "levels": {str(i): preset_for_enforcement_level(i).to_dict() for i in range(11)},
        }
    return mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))


def _profile_from_preset_entry(level: int, entry: dict[str, Any]) -> EnforcementProfile:
    base = preset_for_enforcement_level(level)
    kwargs: dict[str, Any] = {
        "level": level,
        "name": str(entry.get("name") or base.name),
    }
    for key in (
        "ruff_scope",
        "ruff_format_check",
        "tests_mode",
        "coverage_floor",
        "security_mode",
        "pip_audit",
        "e2e_mode",
        "universal_critique",
        "fast_slice_allowed",
        "skip_verdict_policy",
        "milestone_full_ci",
        "terminal_parity_ci",
    ):
        if key in entry and entry[key] is not None:
            kwargs[key] = entry[key]
    return EnforcementProfile(**kwargs)


def resolve_enforcement_profile(
    *,
    level: int | None = None,
    custom_overrides: dict[str, Any] | None = None,
) -> EnforcementProfile:
    if custom_overrides:
        base_level = int(custom_overrides.get("level") or level or 5)
        merged = {**preset_for_enforcement_level(base_level).to_dict(), **custom_overrides}
        profile = _profile_from_preset_entry(base_level, merged)
        return EnforcementProfile(
            level=profile.level,
            name=str(merged.get("name") or profile.name),
            ruff_scope=profile.ruff_scope,
            ruff_format_check=profile.ruff_format_check,
            tests_mode=profile.tests_mode,
            coverage_floor=profile.coverage_floor,
            security_mode=profile.security_mode,
            pip_audit=profile.pip_audit,
            e2e_mode=profile.e2e_mode,
            universal_critique=profile.universal_critique,
            fast_slice_allowed=profile.fast_slice_allowed,
            skip_verdict_policy=profile.skip_verdict_policy,
            milestone_full_ci=profile.milestone_full_ci,
            terminal_parity_ci=profile.terminal_parity_ci,
            custom=True,
        )
    lvl = 5 if level is None else max(0, min(10, level))
    levels = mapping_or_empty(load_enforcement_presets()).get("levels")
    if isinstance(levels, dict):
        entry = mapping_or_empty(levels.get(str(lvl)))
        if entry:
            return _profile_from_preset_entry(lvl, entry)
    return preset_for_enforcement_level(lvl)


def _enforcement_block_from_event_metadata(meta: dict[str, Any]) -> dict[str, Any] | None:
    block = mapping_or_empty(meta.get("enforcement"))
    return block or None


def _profile_from_enforcement_block(block: dict[str, Any]) -> EnforcementProfile:
    level_raw = block.get("level")
    level = int(level_raw) if level_raw is not None else 5
    overrides = {k: v for k, v in block.items() if k not in {"level", "name", "source", "custom"}}
    if overrides:
        return resolve_enforcement_profile(
            level=level, custom_overrides={**overrides, "level": level}
        )
    return resolve_enforcement_profile(level=level)


_RUN_ENFORCEMENT_OVERRIDES: dict[str, dict[str, Any]] = {}


def persist_run_enforcement(
    store: Any,
    run_id: UUID | str,
    profile: EnforcementProfile,
    *,
    tenant_slug: str | None = None,
    repo_root: Path | None = None,
) -> EnforcementProfile:
    from nimbusware_orchestrator.fleet_enforcement_policy import enforce_tenant_enforcement_policy

    profile = enforce_tenant_enforcement_policy(
        profile,
        tenant_slug,
        repo_root=repo_root,
    )
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    block = profile.to_dict()
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"enforcement": block},
            payload=StagePassedPayload(stage_name=ENFORCEMENT_UPDATED_STAGE, duration_ms=0),
        ),
    )
    set_run_enforcement_override(str(rid), profile=profile)
    return profile


def latest_enforcement_block_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(rows):
        pl = mapping_or_empty(row.get("payload"))
        if str(pl.get("stage_name") or "") != ENFORCEMENT_UPDATED_STAGE:
            continue
        block = _enforcement_block_from_event_metadata(mapping_or_empty(row.get("metadata")))
        if block is not None:
            return block
    return None


def set_run_enforcement_override(
    run_id: str,
    *,
    profile: EnforcementProfile | None = None,
    level: int | None = None,
) -> EnforcementProfile:
    resolved = profile or resolve_enforcement_profile(level=level if level is not None else 5)
    _RUN_ENFORCEMENT_OVERRIDES[str(run_id)] = resolved.to_dict()
    return resolved


def enforcement_level_from_rows(rows: list[dict[str, Any]]) -> int:
    persisted = latest_enforcement_block_from_rows(rows)
    if persisted is not None and persisted.get("level") is not None:
        return max(0, min(10, int(persisted["level"])))
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = mapping_or_empty(_RUN_ENFORCEMENT_OVERRIDES.get(rid))
        if override.get("level") is not None:
            return max(0, min(10, int(override["level"])))
    meta = _run_created_metadata(rows)
    if meta:
        for key in ("enforcement_effective", "enforcement"):
            block = mapping_or_empty(meta.get(key))
            if block.get("level") is not None:
                return max(0, min(10, int(block["level"])))
    return 5


def enforcement_profile_from_rows(rows: list[dict[str, Any]]) -> EnforcementProfile:
    persisted = latest_enforcement_block_from_rows(rows)
    if persisted is not None:
        return _profile_from_enforcement_block(persisted)
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = mapping_or_empty(_RUN_ENFORCEMENT_OVERRIDES.get(rid))
        if override.get("level") is not None:
            return _profile_from_enforcement_block(override)
    meta = _run_created_metadata(rows)
    if meta:
        for key in ("enforcement_effective", "enforcement"):
            block = mapping_or_empty(meta.get(key))
            if block.get("level") is not None:
                return _profile_from_enforcement_block(block)
    return resolve_enforcement_profile(level=enforcement_level_from_rows(rows))


def _run_created_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        return mapping_or_empty(row.get("metadata"))
    return {}


def nimbusware_enforcement_depth_enabled() -> bool:
    from nimbusware_env.env_flags import nimbusware_enforcement_depth_enabled as _enabled

    return _enabled()
