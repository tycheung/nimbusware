from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo, fixture_repo_root

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_broken_fixture_repo_tests_fail() -> None:
    root = fixture_repo_root("tiny_broken_app")
    test_file = root / "tests" / "test_calculator.py"
    assert test_file.is_file()
    source = test_file.read_text(encoding="utf-8")
    assert "assert add(2, 3) == 5" in source
    calc = (root / "src" / "app" / "calculator.py").read_text(encoding="utf-8")
    assert "return a + b + 1" in calc


def test_broken_fixture_workspace_attach(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_broken_app", tmp_path / "broken-ws")
    journey_client.attach_project(ws, name="BrokenFixture")
    journey_client.start_micro_slice_run(business_prompt="Broken calculator")
    pending = journey_client.get_pending()
    assert pending["plan_approved"] is False
    assert journey_client.workspace_path == ws.resolve()
