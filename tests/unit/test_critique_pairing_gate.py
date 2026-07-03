from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.app import app
from env import find_repo_root
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.routing import (
    assert_critique_coverage_complete,
    critique_coverage_snapshot,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.registry import RoleRegistry

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_assert_critique_coverage_complete_raises_on_unpaired() -> None:
    snap = {
        "registry_producers": ["planner", "backend_writer"],
        "paired_producers": ["planner"],
        "unpaired_producers": ["backend_writer"],
        "pairing_errors": [],
    }
    with pytest.raises(ValueError, match="unpaired registry producers"):
        assert_critique_coverage_complete(snap)


def test_assert_critique_coverage_complete_raises_on_pairing_errors() -> None:
    snap = {
        "registry_producers": ["planner"],
        "paired_producers": ["planner"],
        "unpaired_producers": [],
        "pairing_errors": [{"producer": "planner", "critic": "missing_critic"}],
    }
    with pytest.raises(ValueError, match="critique pairings invalid"):
        assert_critique_coverage_complete(snap)


def test_create_run_rejects_unpaired_producer_config(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    roles = tmp_path / "configs" / "roles.yaml"
    data = yaml.safe_load(roles.read_text(encoding="utf-8"))
    data["roles"].append(
        {
            "taxonomy_key": "orphan_producer",
            "role_id": "88888888-8888-4888-8888-888888888808",
            "display_name": "Orphan",
        },
    )
    roles.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    orch, _mem = make_dev_orchestrator(tmp_path)
    with pytest.raises(ValueError, match="unpaired registry producers"):
        orch.create_run("default")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_create_run_succeeds_with_complete_pairings(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200, r.text


def test_repo_critique_pairings_cover_all_producers() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    snap = critique_coverage_snapshot(reg, router)
    assert_critique_coverage_complete(snap)
