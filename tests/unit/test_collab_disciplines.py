from __future__ import annotations

from maker.collab.disciplines import (
    discipline_routes,
    list_disciplines,
    normalize_discipline,
    parse_discipline_mentions,
    taxonomy_keys_for_discipline,
)


def test_list_disciplines_includes_core_roles() -> None:
    ids = {d["id"] for d in list_disciplines()}
    assert {"pm", "frontend", "backend", "qa", "architect", "devops"}.issubset(ids)


def test_normalize_discipline_aliases() -> None:
    assert normalize_discipline("fe") == "frontend"
    assert normalize_discipline("@arch") == "architect"
    assert normalize_discipline("unknown") is None


def test_fullstack_multi_taxonomy() -> None:
    keys = taxonomy_keys_for_discipline("fullstack")
    assert keys == ("frontend_writer", "backend_writer")


def test_devops_multi_taxonomy() -> None:
    keys = taxonomy_keys_for_discipline("devops")
    assert keys == ("integration_adapter_writer", "infra_writer")


def test_discipline_routes_from_mentions() -> None:
    routes = discipline_routes("@qa verify checkout")
    assert routes[0]["discipline"] == "qa"
    assert routes[0]["taxonomy_key"] == "test_writer"
    assert routes[0]["source"] == "mention"


def test_participant_hat_when_no_mentions() -> None:
    routes = discipline_routes("Looks good", participant_discipline="backend")
    assert routes[0]["discipline"] == "backend"
    assert routes[0]["source"] == "participant_hat"


def test_parse_discipline_mentions_dedupes() -> None:
    assert parse_discipline_mentions("@frontend @fe same") == ["frontend"]
