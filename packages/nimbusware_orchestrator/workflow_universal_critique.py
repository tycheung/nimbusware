"""Workflow YAML and env overrides for universal post-verify critique panels."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict
from nimbusware_env.env_flags import env_falsy, env_over_yaml


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
    if not isinstance(block, dict):
        return default
    cur = block.get(key)
    return _coerce_yaml_bool(cur, default) if cur is not None else default


def _panel_enabled(
    block: dict[str, object] | None,
    *,
    default_enabled: bool,
) -> bool:
    if not isinstance(block, dict):
        return default_enabled
    if "enabled" in block:
        return _leaf_bool(block, "enabled")
    return default_enabled


def _implementation_panel_flags(
    block: dict[str, object] | None,
    *,
    default_enabled: bool,
) -> tuple[bool, bool]:
    impl_llm = _leaf_bool(block, "llm") if isinstance(block, dict) else False
    impl_stub = _leaf_bool(block, "stub") if isinstance(block, dict) else False
    if default_enabled and isinstance(block, dict) and not impl_llm and not impl_stub:
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
    root = raw.get("universal_critique")
    impl = root.get("implementation") if isinstance(root, dict) else None
    tw = root.get("test_writer") if isinstance(root, dict) else None
    pll = root.get("planner") if isinstance(root, dict) else None
    fw = root.get("frontend_writer") if isinstance(root, dict) else None
    mi = root.get("module_integrator") if isinstance(root, dict) else None

    root_d = root if isinstance(root, dict) else None
    default_enabled = _leaf_bool(root_d, "default_enabled") if root_d else False
    unanimous_gate_enforce = (
        _leaf_bool(root_d, "unanimous_gate_enforce", default=default_enabled) if root_d else False
    )
    impl_d = impl if isinstance(impl, dict) else None
    tw_d = tw if isinstance(tw, dict) else None
    pll_d = pll if isinstance(pll, dict) else None
    fw_d = fw if isinstance(fw, dict) else None
    mi_d = mi if isinstance(mi, dict) else None
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
    return EffectiveUniversalCritique(
        impl_llm=env_over_yaml("NIMBUSWARE_IMPLEMENTATION_CRITIQUE_LLM", wf.impl_llm),
        impl_stub=env_over_yaml("NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS", wf.impl_stub),
        impl_stage_failed_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            wf.impl_stage_failed_on_gate_fail,
        ),
        impl_emit_finding_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            wf.impl_emit_finding_on_gate_fail,
        ),
        impl_hard_block_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            wf.impl_hard_block_on_gate_fail,
        ),
        tw_enabled=env_over_yaml("NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE", wf.tw_enabled),
        tw_llm=env_over_yaml("NIMBUSWARE_TEST_WRITER_CRITIQUE_LLM", wf.tw_llm),
        tw_stub=env_over_yaml("NIMBUSWARE_STUB_TEST_WRITER_CRITICS", wf.tw_stub),
        tw_stage_failed_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_TEST_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            wf.tw_stage_failed_on_gate_fail,
        ),
        tw_emit_finding_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_TEST_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            wf.tw_emit_finding_on_gate_fail,
        ),
        tw_hard_block_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_TEST_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            wf.tw_hard_block_on_gate_fail,
        ),
        pll_enabled=env_over_yaml("NIMBUSWARE_ENABLE_PLANNER_CRITIQUE", wf.pll_enabled),
        pll_llm=env_over_yaml("NIMBUSWARE_PLANNER_CRITIQUE_LLM", wf.pll_llm),
        pll_stub=env_over_yaml("NIMBUSWARE_STUB_PLANNER_CRITICS", wf.pll_stub),
        pll_stage_failed_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_PLANNER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            wf.pll_stage_failed_on_gate_fail,
        ),
        pll_emit_finding_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_PLANNER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            wf.pll_emit_finding_on_gate_fail,
        ),
        pll_hard_block_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_PLANNER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            wf.pll_hard_block_on_gate_fail,
        ),
        fw_enabled=env_over_yaml("NIMBUSWARE_ENABLE_FRONTEND_WRITER_CRITIQUE", wf.fw_enabled),
        fw_llm=env_over_yaml("NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_LLM", wf.fw_llm),
        fw_stub=env_over_yaml("NIMBUSWARE_STUB_FRONTEND_WRITER_CRITICS", wf.fw_stub),
        fw_stage_failed_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            wf.fw_stage_failed_on_gate_fail,
        ),
        fw_emit_finding_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            wf.fw_emit_finding_on_gate_fail,
        ),
        fw_hard_block_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            wf.fw_hard_block_on_gate_fail,
        ),
        mi_enabled=env_over_yaml("NIMBUSWARE_ENABLE_MODULE_INTEGRATOR_CRITIQUE", wf.mi_enabled),
        mi_llm=env_over_yaml("NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_LLM", wf.mi_llm),
        mi_stub=env_over_yaml("NIMBUSWARE_STUB_MODULE_INTEGRATOR_CRITICS", wf.mi_stub),
        mi_stage_failed_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
            wf.mi_stage_failed_on_gate_fail,
        ),
        mi_emit_finding_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
            wf.mi_emit_finding_on_gate_fail,
        ),
        mi_hard_block_on_gate_fail=env_over_yaml(
            "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
            wf.mi_hard_block_on_gate_fail,
        ),
        unanimous_gate_enforce=env_over_yaml(
            "NIMBUSWARE_UNANIMOUS_GATE_ENFORCE",
            wf.unanimous_gate_enforce,
        ),
        default_enabled=wf.default_enabled,
    )
