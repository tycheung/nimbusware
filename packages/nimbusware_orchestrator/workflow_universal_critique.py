from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.mapping import mapping_or_empty
from nimbusware_env.env_flags import (
    env_falsy,
    env_over_yaml,
    env_over_yaml_with_global_fallback,
)
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


def _coerce_yaml_bool(raw: object, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        # Be strict for workflow safety: only 1 / 1.0 enable a knob.
        return raw == 1
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return default


def _leaf_bool(block: dict[str, object] | None, key: str, default: bool = False) -> bool:
    mapping = mapping_or_empty(block)
    if not mapping:
        return default
    cur = mapping.get(key)
    return _coerce_yaml_bool(cur, default) if cur is not None else default


def _panel_enabled(
    block: dict[str, object] | None,
    *,
    default_enabled: bool,
) -> bool:
    mapping = mapping_or_empty(block)
    if not mapping:
        return default_enabled
    if "enabled" in mapping:
        return _leaf_bool(mapping, "enabled")
    return default_enabled


def _implementation_panel_flags(
    block: dict[str, object] | None,
    *,
    default_enabled: bool,
) -> tuple[bool, bool]:
    mapping = mapping_or_empty(block)
    impl_llm = _leaf_bool(mapping, "llm") if mapping else False
    impl_stub = _leaf_bool(mapping, "stub") if mapping else False
    if default_enabled and mapping and not impl_llm and not impl_stub:
        impl_stub = True
    return impl_llm, impl_stub


@dataclass(frozen=True)
class UniversalCritiqueWorkflowBlock:
    """Subset of workflow ``universal_critique`` used after verify."""

    default_enabled: bool = False
    impl_llm: bool = False
    impl_stub: bool = False
    impl_stage_failed_on_gate_fail: bool = False
    impl_emit_finding_on_gate_fail: bool = False
    impl_hard_block_on_gate_fail: bool = False
    tw_enabled: bool = False
    tw_llm: bool = False
    tw_stub: bool = False
    tw_stage_failed_on_gate_fail: bool = False
    tw_emit_finding_on_gate_fail: bool = False
    tw_hard_block_on_gate_fail: bool = False
    pll_enabled: bool = False
    pll_llm: bool = False
    pll_stub: bool = False
    pll_stage_failed_on_gate_fail: bool = False
    pll_emit_finding_on_gate_fail: bool = False
    pll_hard_block_on_gate_fail: bool = False
    fw_enabled: bool = False
    fw_llm: bool = False
    fw_stub: bool = False
    fw_stage_failed_on_gate_fail: bool = False
    fw_emit_finding_on_gate_fail: bool = False
    fw_hard_block_on_gate_fail: bool = False
    mi_enabled: bool = False
    mi_llm: bool = False
    mi_stub: bool = False
    mi_stage_failed_on_gate_fail: bool = False
    mi_emit_finding_on_gate_fail: bool = False
    mi_hard_block_on_gate_fail: bool = False
    unanimous_gate_enforce: bool = False


def parse_universal_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> UniversalCritiqueWorkflowBlock:
    """Read ``universal_critique`` from workflow YAML; missing block → defaults (all false)."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return UniversalCritiqueWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return UniversalCritiqueWorkflowBlock()
    root_d = mapping_or_empty(raw.get("universal_critique"))
    impl_d = mapping_or_empty(root_d.get("implementation"))
    tw_d = mapping_or_empty(root_d.get("test_writer"))
    pll_d = mapping_or_empty(root_d.get("planner"))
    fw_d = mapping_or_empty(root_d.get("frontend_writer"))
    mi_d = mapping_or_empty(root_d.get("module_integrator"))

    default_enabled = _leaf_bool(root_d, "default_enabled") if root_d else False
    unanimous_gate_enforce = (
        _leaf_bool(root_d, "unanimous_gate_enforce", default=default_enabled) if root_d else False
    )
    impl_llm, impl_stub = _implementation_panel_flags(
        impl_d,
        default_enabled=default_enabled,
    )

    return UniversalCritiqueWorkflowBlock(
        default_enabled=default_enabled,
        impl_llm=impl_llm,
        impl_stub=impl_stub,
        impl_stage_failed_on_gate_fail=_leaf_bool(impl_d, "stage_failed_on_gate_fail"),
        impl_emit_finding_on_gate_fail=_leaf_bool(impl_d, "emit_finding_on_gate_fail"),
        impl_hard_block_on_gate_fail=_leaf_bool(impl_d, "hard_block_on_gate_fail"),
        tw_enabled=_panel_enabled(tw_d, default_enabled=default_enabled),
        tw_llm=_leaf_bool(tw_d, "llm"),
        tw_stub=_leaf_bool(tw_d, "stub"),
        tw_stage_failed_on_gate_fail=_leaf_bool(tw_d, "stage_failed_on_gate_fail"),
        tw_emit_finding_on_gate_fail=_leaf_bool(tw_d, "emit_finding_on_gate_fail"),
        tw_hard_block_on_gate_fail=_leaf_bool(tw_d, "hard_block_on_gate_fail"),
        pll_enabled=_panel_enabled(pll_d, default_enabled=default_enabled),
        pll_llm=_leaf_bool(pll_d, "llm"),
        pll_stub=_leaf_bool(pll_d, "stub"),
        pll_stage_failed_on_gate_fail=_leaf_bool(pll_d, "stage_failed_on_gate_fail"),
        pll_emit_finding_on_gate_fail=_leaf_bool(pll_d, "emit_finding_on_gate_fail"),
        pll_hard_block_on_gate_fail=_leaf_bool(pll_d, "hard_block_on_gate_fail"),
        fw_enabled=_panel_enabled(fw_d, default_enabled=default_enabled),
        fw_llm=_leaf_bool(fw_d, "llm"),
        fw_stub=_leaf_bool(fw_d, "stub"),
        fw_stage_failed_on_gate_fail=_leaf_bool(fw_d, "stage_failed_on_gate_fail"),
        fw_emit_finding_on_gate_fail=_leaf_bool(fw_d, "emit_finding_on_gate_fail"),
        fw_hard_block_on_gate_fail=_leaf_bool(fw_d, "hard_block_on_gate_fail"),
        mi_enabled=_panel_enabled(mi_d, default_enabled=default_enabled),
        mi_llm=_leaf_bool(mi_d, "llm"),
        mi_stub=_leaf_bool(mi_d, "stub"),
        mi_stage_failed_on_gate_fail=_leaf_bool(mi_d, "stage_failed_on_gate_fail"),
        mi_emit_finding_on_gate_fail=_leaf_bool(mi_d, "emit_finding_on_gate_fail"),
        mi_hard_block_on_gate_fail=_leaf_bool(mi_d, "hard_block_on_gate_fail"),
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


_UC_PANEL_KILL_SWITCH_KEYS = (
    "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS",
    "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE",
    "NIMBUSWARE_ENABLE_PLANNER_CRITIQUE",
    "NIMBUSWARE_ENABLE_FRONTEND_WRITER_CRITIQUE",
    "NIMBUSWARE_ENABLE_MODULE_INTEGRATOR_CRITIQUE",
)


def universal_critique_production_default_on(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """True when workflow ``default_enabled`` and no panel master kill-switch is explicitly off."""
    wf = parse_universal_critique_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not wf.default_enabled:
        return False
    for key in _UC_PANEL_KILL_SWITCH_KEYS:
        if env_falsy(key):
            return False
    return True


@dataclass(frozen=True)
class EffectiveUniversalCritique:
    """YAML + optional env overrides for post-verify critique (single resolved view)."""

    impl_llm: bool
    impl_stub: bool
    impl_stage_failed_on_gate_fail: bool
    impl_emit_finding_on_gate_fail: bool
    impl_hard_block_on_gate_fail: bool
    tw_enabled: bool
    tw_llm: bool
    tw_stub: bool
    tw_stage_failed_on_gate_fail: bool
    tw_emit_finding_on_gate_fail: bool
    tw_hard_block_on_gate_fail: bool
    pll_enabled: bool
    pll_llm: bool
    pll_stub: bool
    pll_stage_failed_on_gate_fail: bool
    pll_emit_finding_on_gate_fail: bool
    pll_hard_block_on_gate_fail: bool
    fw_enabled: bool = False
    fw_llm: bool = False
    fw_stub: bool = False
    fw_stage_failed_on_gate_fail: bool = False
    fw_emit_finding_on_gate_fail: bool = False
    fw_hard_block_on_gate_fail: bool = False
    mi_enabled: bool = False
    mi_llm: bool = False
    mi_stub: bool = False
    mi_stage_failed_on_gate_fail: bool = False
    mi_emit_finding_on_gate_fail: bool = False
    mi_hard_block_on_gate_fail: bool = False
    unanimous_gate_enforce: bool = False
    default_enabled: bool = False


_UC_STAGE_FAILED_GLOBAL = "NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL"
_UC_EMIT_FINDING_GLOBAL = "NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL"
_UC_HARD_BLOCK_GLOBAL = "NIMBUSWARE_UNIVERSAL_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL"

_UC_ENV_FIELDS: tuple[tuple[str, str], ...] = (
    ("impl_llm", "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_LLM"),
    ("impl_stub", "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS"),
    ("tw_enabled", "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE"),
    ("tw_llm", "NIMBUSWARE_TEST_WRITER_CRITIQUE_LLM"),
    ("tw_stub", "NIMBUSWARE_STUB_TEST_WRITER_CRITICS"),
    ("pll_enabled", "NIMBUSWARE_ENABLE_PLANNER_CRITIQUE"),
    ("pll_llm", "NIMBUSWARE_PLANNER_CRITIQUE_LLM"),
    ("pll_stub", "NIMBUSWARE_STUB_PLANNER_CRITICS"),
    ("fw_enabled", "NIMBUSWARE_ENABLE_FRONTEND_WRITER_CRITIQUE"),
    ("fw_llm", "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_LLM"),
    ("fw_stub", "NIMBUSWARE_STUB_FRONTEND_WRITER_CRITICS"),
    ("mi_enabled", "NIMBUSWARE_ENABLE_MODULE_INTEGRATOR_CRITIQUE"),
    ("mi_llm", "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_LLM"),
    ("mi_stub", "NIMBUSWARE_STUB_MODULE_INTEGRATOR_CRITICS"),
    ("unanimous_gate_enforce", "NIMBUSWARE_UNANIMOUS_GATE_ENFORCE"),
)

_UC_GATE_FAIL_ENV_FIELDS: tuple[tuple[str, str, str], ...] = (
    (
        "impl_stage_failed_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        _UC_STAGE_FAILED_GLOBAL,
    ),
    (
        "impl_emit_finding_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        _UC_EMIT_FINDING_GLOBAL,
    ),
    (
        "impl_hard_block_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        _UC_HARD_BLOCK_GLOBAL,
    ),
    (
        "tw_stage_failed_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        _UC_STAGE_FAILED_GLOBAL,
    ),
    (
        "tw_emit_finding_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        _UC_EMIT_FINDING_GLOBAL,
    ),
    (
        "tw_hard_block_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        _UC_HARD_BLOCK_GLOBAL,
    ),
    (
        "pll_stage_failed_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        _UC_STAGE_FAILED_GLOBAL,
    ),
    (
        "pll_emit_finding_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        _UC_EMIT_FINDING_GLOBAL,
    ),
    (
        "pll_hard_block_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        _UC_HARD_BLOCK_GLOBAL,
    ),
    (
        "fw_stage_failed_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        _UC_STAGE_FAILED_GLOBAL,
    ),
    (
        "fw_emit_finding_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        _UC_EMIT_FINDING_GLOBAL,
    ),
    (
        "fw_hard_block_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        _UC_HARD_BLOCK_GLOBAL,
    ),
    (
        "mi_stage_failed_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        _UC_STAGE_FAILED_GLOBAL,
    ),
    (
        "mi_emit_finding_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        _UC_EMIT_FINDING_GLOBAL,
    ),
    (
        "mi_hard_block_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        _UC_HARD_BLOCK_GLOBAL,
    ),
)


def effective_universal_critique(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> EffectiveUniversalCritique:
    wf = parse_universal_critique_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    resolved = {
        field: env_over_yaml(env_key, getattr(wf, field)) for field, env_key in _UC_ENV_FIELDS
    }
    for field, panel_key, global_key in _UC_GATE_FAIL_ENV_FIELDS:
        resolved[field] = env_over_yaml_with_global_fallback(
            panel_key,
            global_key,
            getattr(wf, field),
        )
    resolved["default_enabled"] = wf.default_enabled
    return EffectiveUniversalCritique(**resolved)
