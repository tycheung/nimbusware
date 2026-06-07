from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo, fixture_repo_root

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_tiny_api_app_fixture_exists() -> None:
    root = fixture_repo_root("tiny_api_app")
    assert (root / "src" / "app" / "routes.py").is_file()


def test_tiny_api_app_fixture_copy(tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "api-ws")
    assert (ws / "src" / "app" / "routes.py").is_file()


def test_tiny_api_micro_slice_attach_journey(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "api-journey")
    orch_dir = ws / "packages" / "nimbusware_orchestrator"
    orch_dir.mkdir(parents=True, exist_ok=True)
    (orch_dir / "micro_slice.py").write_text("# api stub\n", encoding="utf-8")
    (orch_dir / "slice_gate.py").write_text("# gate stub\n", encoding="utf-8")

    journey_client.attach_project(ws, name="TinyApiFixture")
    journey_client.start_micro_slice_run(business_prompt="REST contacts API")
    pending = journey_client.get_pending()
    assert pending["plan_approved"] is False
    assert (journey_client.workspace_path / "src" / "app" / "routes.py").is_file()
