"""Workflow YAML + env knobs for parallel writer dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import env_force_off, env_force_on
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


def _coerce_yaml_bool(raw: object, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw == 1
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return default


@dataclass(frozen=True)
class ParallelWritersWorkflowBlock:
    enabled: bool = False
    test_writer_stage_enabled: bool = False
    test_writer_llm_body_enabled: bool = False
    test_writer_llm_stub_fallback: bool = False


def parse_parallel_writers_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> ParallelWritersWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return ParallelWritersWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return ParallelWritersWorkflowBlock()
    block = raw.get("parallel_writers")
    if not isinstance(block, dict):
        return ParallelWritersWorkflowBlock()
    tw = block.get("test_writer_stage")
    tw_enabled = False
    tw_llm_enabled = False
    tw_llm_stub_fallback = False
    if isinstance(tw, dict):
        tw_enabled = _coerce_yaml_bool(tw.get("enabled"))
        tw_llm_enabled = _coerce_yaml_bool(tw.get("llm_body_enabled"))
        tw_llm_stub_fallback = _coerce_yaml_bool(tw.get("llm_stub_fallback"))
    elif tw is not None:
        tw_enabled = _coerce_yaml_bool(tw)
    return ParallelWritersWorkflowBlock(
        enabled=_coerce_yaml_bool(block.get("enabled")),
        test_writer_stage_enabled=tw_enabled,
        test_writer_llm_body_enabled=tw_llm_enabled,
        test_writer_llm_stub_fallback=tw_llm_stub_fallback,
    )


def max_parallel_writer_stages_from_governor() -> int | None:
    try:
        from nimbusware_hw.cache import get_cached_profile
        from nimbusware_hw.governor import governor_for_profile
        from nimbusware_hw.pressure import pressure_limits_parallel, sample_pressure

        gov = governor_for_profile(get_cached_profile())
        level, _ = sample_pressure(gov)
        return pressure_limits_parallel(level, gov.max_parallel_writer_stages)
    except ImportError:
        return None


def parallel_writers_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """``NIMBUSWARE_PARALLEL_WRITERS=1`` forces on; ``0``/``false``/``no`` forces off."""
    if env_force_off("NIMBUSWARE_PARALLEL_WRITERS"):
        return False
    if env_force_on("NIMBUSWARE_PARALLEL_WRITERS"):
        return True
    cap = max_parallel_writer_stages_from_governor()
    if cap is not None and cap < 2:
        return False
    wf = parse_parallel_writers_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return wf.enabled


def test_writer_stage_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    if env_force_off("NIMBUSWARE_TEST_WRITER_STAGE"):
        return False
    if env_force_on("NIMBUSWARE_TEST_WRITER_STAGE"):
        return True
    wf = parse_parallel_writers_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return wf.test_writer_stage_enabled


def test_writer_llm_body_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    if env_force_off("NIMBUSWARE_TEST_WRITER_LLM_BODY"):
        return False
    if env_force_on("NIMBUSWARE_TEST_WRITER_LLM_BODY"):
        return True
    wf = parse_parallel_writers_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return wf.test_writer_llm_body_enabled


def test_writer_llm_stub_fallback(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    if env_force_off("NIMBUSWARE_TEST_WRITER_LLM_STUB"):
        return False
    if env_force_on("NIMBUSWARE_TEST_WRITER_LLM_STUB"):
        return True
    wf = parse_parallel_writers_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return wf.test_writer_llm_stub_fallback
