from __future__ import annotations

import tarfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import yaml

from env import find_repo_root
from orchestrator.critique.routing import extra_critics_for_surface
from orchestrator.factory.factory_flows import match_factory_flow_id
from orchestrator.factory.runtime import resolve_put_stack_from_manifest
from orchestrator.replay.audit_export import (
    build_audit_bundle_bytes,
    scope_snapshot_from_requirements,
    surface_outcomes_from_events,
)
from orchestrator.routing.preflight import surface_binding_rows
from orchestrator.stack.agent_scaffold import scaffold_agents_for_manifest
from research.bundle_promotion import (
    list_catalog_candidates_for_stack,
    primary_stack_id_from_requirements,
    write_catalog_candidate,
)

REPO = find_repo_root()
_MANIFEST = {
    "surfaces": ["web", "api"],
    "stacks": {"web": "react_vite", "api": "fastapi_python"},
}


def test_put_manifest_and_factory_synergy(tmp_path: Path) -> None:
    assert resolve_put_stack_from_manifest(_MANIFEST, tmp_path) == "fullstack"
    assert match_factory_flow_id("todo app", stack_manifest=_MANIFEST, repo_root=REPO) == "todo_api"
    static = {"surfaces": ["web"], "stacks": {"web": "react_vite"}}
    assert (
        match_factory_flow_id("landing page", stack_manifest=static, repo_root=REPO)
        == "static_site"
    )


def test_scope_bindings_critics_and_catalog(tmp_path: Path) -> None:
    rows = surface_binding_rows(REPO, _MANIFEST)
    assert {row["surface_id"] for row in rows} == {"web", "api"}
    assert "launch_test_critic" in extra_critics_for_surface("web", REPO)
    run_id = uuid4()
    write_catalog_candidate(
        tmp_path,
        run_id=run_id,
        candidate_id="pattern-a",
        bundle_hints={"stack_id": "fastapi_python"},
    )
    write_catalog_candidate(
        tmp_path,
        run_id=run_id,
        candidate_id="pattern-b",
        bundle_hints={"stack_id": "react_vite"},
    )
    assert (
        list_catalog_candidates_for_stack(tmp_path, "fastapi_python")[0]["candidate_id"]
        == "pattern-a"
    )
    req = {"stack_manifest": _MANIFEST}
    assert primary_stack_id_from_requirements(req) == "fastapi_python"


def test_scaffold_agents_for_manifest(tmp_path: Path) -> None:
    registry_path = tmp_path / "configs" / "custom_agents" / "registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text("agents: []\n", encoding="utf-8")
    stacks_dir = tmp_path / "configs" / "stacks"
    stacks_dir.mkdir(parents=True)
    (stacks_dir / "catalog.yaml").write_text(
        "stacks:\n  - id: fastapi_python\n    path: fastapi_python.yaml\n",
        encoding="utf-8",
    )
    (stacks_dir / "fastapi_python.yaml").write_text(
        (REPO / "configs/stacks/fastapi_python.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    manifest = {
        "surfaces": ["api"],
        "stacks": {"api": "fastapi_python"},
        "frozen": True,
        "version": 1,
    }
    created = scaffold_agents_for_manifest(manifest, repo_root=tmp_path, persist=True)
    saved = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert "fastapi_python_writer" in created
    assert "fastapi_python_writer" in {item["id"] for item in saved.get("agents", [])}


def test_audit_bundle_scope_and_surface_outcomes() -> None:
    requirements = {
        "stack_manifest": {"surfaces": ["api"], "stacks": {"api": "fastapi_python"}, "version": 1},
    }
    scope = scope_snapshot_from_requirements(requirements)
    outcomes = surface_outcomes_from_events([]) or [
        {"surface_id": "api", "slice_count": 1, "passed": 1, "failed": 0, "planned": 0},
    ]
    bundle = build_audit_bundle_bytes(
        run_id="run-1",
        events=[],
        policy_snapshot={"policy_version": "1"},
        scope_snapshot=scope,
        surface_outcomes=outcomes,
    )
    with tarfile.open(fileobj=BytesIO(bundle), mode="r:gz") as tar:
        names = {member.name for member in tar.getmembers()}
    assert {"scope_snapshot.json", "surface_outcomes.json"} <= names
