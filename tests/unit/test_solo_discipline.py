from __future__ import annotations

from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_maker.solo_discipline import parse_discipline_mentions, solo_discipline_routes


def test_parse_discipline_mentions_aliases() -> None:
    assert parse_discipline_mentions("Please @fe fix the form") == ["frontend"]
    assert parse_discipline_mentions("@backend and @qa review") == ["backend", "qa"]


def test_solo_hat_route_when_no_mentions() -> None:
    routes = solo_discipline_routes("Ship the login page", solo_hat="architect")
    assert len(routes) == 1
    assert routes[0]["discipline"] == "architect"
    assert routes[0]["source"] == "solo_hat"


def test_mentions_override_hat() -> None:
    routes = solo_discipline_routes("@qa please verify", solo_hat="backend")
    assert routes[0]["discipline"] == "qa"
    assert routes[0]["source"] == "mention"


def test_requirements_artifact_includes_routes() -> None:
    artifact = build_requirements_artifact(
        business_prompt="@frontend polish the dashboard",
        solo_discipline="backend",
    )
    routes = artifact.get("solo_discipline_routes")
    assert isinstance(routes, list)
    assert routes[0]["discipline"] == "frontend"
