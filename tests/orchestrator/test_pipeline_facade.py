"""Pipeline facade — composed mixins and stable patch target (Phase 6)."""

from __future__ import annotations

from pathlib import Path

import nimbusware_orchestrator.pipeline as pipeline_module
from nimbusware_orchestrator.pipeline import RunOrchestrator, default_paths, make_dev_orchestrator
from nimbusware_env import find_repo_root


def test_pipeline_exports_public_api() -> None:
    assert RunOrchestrator is not None
    assert callable(default_paths)
    assert callable(make_dev_orchestrator)


def test_pipeline_module_exposes_patch_targets() -> None:
    for name in (
        "run_writer_verifier_bundle",
        "load_anti_deadlock_settings",
        "parse_agent_evaluator_workflow_block",
        "execute_plan_stage_llm",
        "time",
    ):
        assert hasattr(pipeline_module, name), name


def test_make_dev_orchestrator_returns_orchestrator() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, mem = make_dev_orchestrator(repo)
    assert isinstance(orch, RunOrchestrator)
    assert hasattr(mem, "append")


def test_pipeline_internal_package_exists() -> None:
    from nimbusware_orchestrator._pipeline import compose

    assert hasattr(compose, "build_run_orchestrator_class")


def test_pipeline_mixin_modules_exist() -> None:
    from nimbusware_orchestrator._pipeline import (
        base,
        create_run,
        critique_gates,
        lifecycle,
        optional_stages,
        writers,
    )

    for mod in (
        base,
        create_run,
        lifecycle,
        writers,
        critique_gates,
        optional_stages,
    ):
        assert mod.__name__.startswith("nimbusware_orchestrator._pipeline.")


def test_run_orchestrator_has_core_methods() -> None:
    for name in (
        "create_run",
        "start_run_after_preflight",
        "execute_plan_stage",
        "execute_writer_verifier_pass",
        "run_optional_scraper_fetch_stage",
        "_emit_bundle_integrator_gate",
    ):
        assert hasattr(RunOrchestrator, name), name
