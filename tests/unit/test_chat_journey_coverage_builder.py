from __future__ import annotations

from nimbusware_projections.builders.chat_journey_coverage import (
    build_chat_journey_coverage,
    chat_journey_scenarios_path,
)


def test_chat_journey_scenarios_path_points_at_repo_yaml() -> None:
    path = chat_journey_scenarios_path()
    assert path.name == "chat_journey_scenarios.yaml"
    assert path.is_file()


def test_build_chat_journey_coverage_meets_gate() -> None:
    body = build_chat_journey_coverage()
    assert body["scenario_count"] >= 1
    assert body["wired_count"] >= 1
    assert body["coverage_rate"] is not None
    assert body["target_rate"] == 0.80
    assert body["meets_target"] is True
