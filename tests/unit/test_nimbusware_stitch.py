from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from agent_core.models import EventType
from config.materializer import ConfigMaterializer
from config.seed import seed_config_from_repo
from config.store import InMemoryConfigStore
from env import find_repo_root
from maker.slice_workflow.approval_panel import revert_workspace
from maker.workspace.workspace import project_metadata_block
from orchestrator.pipeline import RunOrchestrator, default_paths
from research.stitch_manifests import (
    persist_transplant_manifest,
    read_transplant_manifest,
)
from research.stitch_models import TransplantManifest
from research.stitch_read_model import stitch_applied_snapshot_from_events
from store.allowed_types import allowed_event_type_values
from store.memory import InMemoryEventStore


def test_stitch_event_types_in_db_allowlist() -> None:
    allowed = allowed_event_type_values()
    for et in (
        EventType.STITCH_LICENSE_CHECKED,
        EventType.STITCH_DEPENDENCY_CHECKED,
        EventType.STITCH_PLAN_EMITTED,
        EventType.STITCH_APPLIED,
        EventType.STITCH_FAILED,
    ):
        assert et.value in allowed


def test_license_check_passes_for_mit_allowlist() -> None:
    from research.stitch_verifiers import license_check_passes

    result = license_check_passes(("MIT",), ["MIT", "Apache-2.0"])
    assert result.passed is True


def test_license_check_fails_for_disallowed_license() -> None:
    from research.stitch_verifiers import license_check_passes

    result = license_check_passes(("GPL-3.0",), ["MIT"])
    assert result.passed is False


def test_dependency_check_fails_when_max_zero() -> None:
    from research.stitch_verifiers import dependency_diff_check

    result = dependency_diff_check(["stub-transplant-runtime"], max_new_dependencies=0)
    assert result.passed is False
    assert result.reason_code == "exceeds_max_new_dependencies"


def test_transplant_manifest_round_trip(tmp_path: Path) -> None:
    manifest = TransplantManifest(
        manifest_id="manifest-test-1",
        source_kind="stub",
        source_tree_hash="stub:abc12345",
        file_paths=("packages/stub_transplant/__init__.py",),
        license_paths=("LICENSE",),
        required_env_vars=(),
    )
    persist_transplant_manifest(tmp_path, manifest)
    loaded = read_transplant_manifest(tmp_path, "manifest-test-1")
    assert loaded is not None
    assert loaded.source_kind == "stub"


def test_stitch_budget_max_files_emits_failed(tmp_path: Path) -> None:
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.registry import RoleRegistry
    from research.stages_stitch import emit_stitch_stages_stub

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml",
    )
    store = InMemoryEventStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "packages").mkdir(parents=True)
    meta = {
        "project": project_metadata_block(
            project_id=uuid4(),
            name="stitch-test",
            workspace_path=ws,
            template="attach",
        ),
        "stitch": {"max_files": 1, "max_loc": 2500, "max_new_dependencies": 10},
    }
    prior = [
        {
            "event_type": EventType.RESEARCH_BRIEF_EMITTED.value,
            "payload": {"brief_kind": "code", "artifact_id": "a1"},
        },
    ]
    applied = emit_stitch_stages_stub(
        store,
        reg,
        router,
        run_id=run_id,
        repo_root=tmp_path,
        run_created_metadata=meta,
        stitch_meta=meta["stitch"],
        prior_events=prior,
    )
    assert applied is False
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.STITCH_FAILED.value in types


def test_execute_plan_stage_emits_stitch_and_post_refactor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    ev_store = InMemoryEventStore()
    ws = tmp_path / "project_ws"
    ws.mkdir()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_RESEARCH", "1")
    monkeypatch.setenv("NIMBUSWARE_STITCH", "1")
    run_id = orch.create_run(
        "default",
        project_id=uuid4(),
        project_name="stitch",
        project_workspace_path=str(ws),
        requirements={"business_prompt": "Build auth module with OSS transplant."},
    )
    orch.execute_plan_stage(run_id)
    types = [r.get("event_type") for r in ev_store.list_run_events(str(run_id))]
    assert EventType.STITCH_LICENSE_CHECKED.value in types
    assert EventType.STITCH_DEPENDENCY_CHECKED.value in types
    assert EventType.STITCH_PLAN_EMITTED.value in types
    assert EventType.STITCH_APPLIED.value in types
    license_row = next(
        r
        for r in ev_store.list_run_events(str(run_id))
        if r.get("event_type") == EventType.STITCH_LICENSE_CHECKED.value
    )
    assert license_row["payload"]["passed"] is True
    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in ev_store.list_run_events(str(run_id))
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "refactor.post_stitch" in stages


def test_revert_workspace_restores_pre_stitch_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    ev_store = InMemoryEventStore()
    ws = tmp_path / "project_ws"
    ws.mkdir()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_RESEARCH", "1")
    monkeypatch.setenv("NIMBUSWARE_STITCH", "1")
    run_id = orch.create_run(
        "default",
        project_id=uuid4(),
        project_name="stitch-revert",
        project_workspace_path=str(ws),
        requirements={"business_prompt": "Auth transplant path."},
    )
    orch.execute_plan_stage(run_id)
    stub_file = ws / "packages" / "stub_transplant" / "__init__.py"
    assert stub_file.is_file()
    snap = stitch_applied_snapshot_from_events(ev_store.list_run_events(str(run_id)))
    assert snap is not None
    result = revert_workspace(orch, run_id)
    assert result["status"] == "reverted"
    assert not stub_file.is_file()


def test_stitch_license_fail_blocks_plan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.registry import RoleRegistry
    from research import stages_stitch
    from research.stages_stitch import emit_stitch_stages_stub

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml",
    )
    store = InMemoryEventStore()
    run_id = uuid4()
    ws = tmp_path / "ws"
    ws.mkdir()
    meta = {
        "project": project_metadata_block(
            project_id=uuid4(),
            name="lic-fail",
            workspace_path=ws,
            template="attach",
        ),
        "stitch": {
            "max_files": 40,
            "max_loc": 2500,
            "max_new_dependencies": 10,
            "license_allowlist": ["MIT"],
        },
    }
    prior = [
        {
            "event_type": EventType.RESEARCH_BRIEF_EMITTED.value,
            "payload": {"brief_kind": "code", "artifact_id": "a1"},
        },
    ]

    def _bad_licenses(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ("GPL-3.0",)

    monkeypatch.setattr(stages_stitch, "scan_manifest_licenses", _bad_licenses)
    applied = emit_stitch_stages_stub(
        store,
        reg,
        router,
        run_id=run_id,
        repo_root=tmp_path,
        run_created_metadata=meta,
        stitch_meta=meta["stitch"],
        prior_events=prior,
    )
    assert applied is False
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.STITCH_FAILED.value in types
    assert EventType.STITCH_PLAN_EMITTED.value not in types


def test_require_refactor_pass_false_skips_post_stitch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from config.keys import NS_WORKFLOWS

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    custom = dict(mat.get_workflow_profile_dict("default"))
    custom["stitch"] = {
        "enabled": True,
        "max_files": 40,
        "max_loc": 2500,
        "max_new_dependencies": 10,
        "require_refactor_pass": False,
    }
    cfg_store.upsert(NS_WORKFLOWS, "stitch_no_refactor", custom)
    ev_store = InMemoryEventStore()
    ws = tmp_path / "ws2"
    ws.mkdir()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_RESEARCH", "1")
    monkeypatch.setenv("NIMBUSWARE_STITCH", "1")
    run_id = orch.create_run(
        "stitch_no_refactor",
        project_id=uuid4(),
        project_name="no-refactor",
        project_workspace_path=str(ws),
        requirements={"business_prompt": "Auth transplant."},
    )
    orch.execute_plan_stage(run_id)
    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in ev_store.list_run_events(str(run_id))
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "refactor.post_stitch" not in stages
