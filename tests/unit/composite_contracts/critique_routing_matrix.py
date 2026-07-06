from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from unit.composite_orchestrator_fixtures import (
    CANONICAL_CRITICS,
    CANONICAL_DEFAULT_CRITICS,
    CANONICAL_PRODUCERS,
    deterministic_uuid,
)

_EXPECTED_TAIL = ("configs", "personas", "critique_pairings.yaml")

REPO_PAIRINGS: dict[str, tuple[str, ...]] = {
    "planner": CANONICAL_CRITICS,
    "backend_writer": (
        "product_reference_critic",
        "domain_critic",
        "security_critic",
        "performance_critic",
        "network_resilience_critic",
    ),
    "test_writer": CANONICAL_CRITICS,
}

CANONICAL_LIFECYCLE_KEYS = [
    "backend_writer",
    "domain_critic",
    "planner",
    "product_reference_critic",
    "test_writer",
]

DEFAULT_CRITICS_FALLBACK_KEYS = [
    "domain_critic",
    "product_reference_critic",
    "unknown_producer",
]

_SUFFIX_BOUNDARY_REGISTRY = {
    "critic": deterministic_uuid(20),
    "critic_helper": deterministic_uuid(21),
    "x_critic_y": deterministic_uuid(22),
    "criticism_team": deterministic_uuid(23),
    "_critic": deterministic_uuid(30),
    "super_critic": deterministic_uuid(31),
    "planner_critic": deterministic_uuid(32),
    "domain_critic": deterministic_uuid(33),
}

_ALL_CRITIC_REGISTRY = {
    "a_critic": deterministic_uuid(10),
    "b_critic": deterministic_uuid(11),
    "domain_critic": deterministic_uuid(12),
    "product_reference_critic": deterministic_uuid(13),
}


def _validate_a1_return_type(_case: dict[str, Any], actual: Path) -> None:
    assert isinstance(actual, Path)
    assert not isinstance(actual, str)


def _validate_a2_three_segment(case: dict[str, Any], actual: Path) -> None:
    root = case["resolved_root"]
    assert actual == root / "configs" / "personas" / "critique_pairings.yaml"
    assert actual.parts[-3:] == _EXPECTED_TAIL


def _validate_a3_yaml_suffix(_case: dict[str, Any], actual: Path) -> None:
    assert actual.suffix == ".yaml"
    assert actual.name == "critique_pairings.yaml"
    assert actual.suffix != ".yml"


def _validate_a4_pure_function(_case: dict[str, Any], actual: Path) -> None:
    ghost = _case["ghost_root"]
    assert isinstance(actual, Path)
    assert not actual.exists()
    assert actual.parent.parent.parent == ghost


def _validate_a5_absolute(case: dict[str, Any], actual: Path) -> None:
    root = case["resolved_root"]
    assert root.is_absolute()
    assert actual.is_absolute()
    assert actual == root / "configs" / "personas" / "critique_pairings.yaml"


def _validate_a5_relative(case: dict[str, Any], actual: Path) -> None:
    root = case["resolved_root"]
    assert not root.is_absolute()
    assert not actual.is_absolute()
    assert actual == root / "configs" / "personas" / "critique_pairings.yaml"


def _validate_b1_repo_pairings(_case: dict[str, Any], router: Any) -> None:
    for producer, expected in REPO_PAIRINGS.items():
        paired = router.pairing_for(producer)
        assert sorted(paired) == sorted(expected), f"producer {producer!r} pairing drift"


def _validate_b2_default_critics(_case: dict[str, Any], router: Any) -> None:
    for producer in ("any-producer", "planner", "unknown_role"):
        paired = router.pairing_for(producer)
        assert tuple(paired) == CANONICAL_DEFAULT_CRITICS


def _validate_c2_frozenset_immutable(_case: dict[str, Any], result: frozenset[str]) -> None:
    assert type(result) is frozenset
    with pytest.raises(AttributeError):
        result.add("x")  # type: ignore[attr-defined]
    canary = {result: "ok"}
    assert canary[result] == "ok"


def _validate_c3_empty(_case: dict[str, Any], result: frozenset[str]) -> None:
    assert result == frozenset()
    assert len(result) == 0
    assert type(result) is frozenset


def _validate_c5_suffix_boundary(_case: dict[str, Any], result: frozenset[str]) -> None:
    assert result == frozenset({"critic", "critic_helper", "x_critic_y", "criticism_team"})
    for filtered_key in {"_critic", "super_critic", "planner_critic", "domain_critic"}:
        assert filtered_key not in result
        assert filtered_key.endswith("_critic")


def _validate_c6_agent_evaluator(_case: dict[str, Any], result: frozenset[str]) -> None:
    assert "planner" in result
    assert "agent_evaluator" not in result


def _validate_d1_canonical(_case: dict[str, Any], result: list[str]) -> None:
    assert result == CANONICAL_LIFECYCLE_KEYS
    assert len(result) == len(set(result)) == 5


def _validate_d2_sorted_idempotent(case: dict[str, Any], result: list[str]) -> None:
    assert type(result) is list
    assert not isinstance(result, (set, frozenset))
    assert result == sorted(result)
    assert result == sorted(set(result))
    assert result == case["second_call"]


def _validate_d4_empty_producers(case: dict[str, Any], result: list[str]) -> None:
    strict_router = case["strict_router"]
    assert result == []
    assert strict_router.pairing_for.called is False
    assert strict_router.pairing_for.call_count == 0


PATH_COMPOSITION_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a1_return_type", "root_kind": "repo", "validate": _validate_a1_return_type},
    {"case_id": "a2_three_segment", "root_kind": "repo", "validate": _validate_a2_three_segment},
    {"case_id": "a3_yaml_suffix", "root_kind": "repo", "validate": _validate_a3_yaml_suffix},
    {"case_id": "a4_pure_function", "root_kind": "ghost", "validate": _validate_a4_pure_function},
    {"case_id": "a5_absolute", "root_kind": "repo", "validate": _validate_a5_absolute},
    {
        "case_id": "a5_relative",
        "root_kind": "relative",
        "relative_root": Path("rel/y"),
        "validate": _validate_a5_relative,
    },
)

LOAD_ROUTER_VALUE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "b1_repo_happy_path", "root_kind": "repo", "validate": _validate_b1_repo_pairings},
    {
        "case_id": "b2_empty_pairings",
        "root_kind": "tmp",
        "yaml_body": "version: 1\n",
        "validate": _validate_b2_default_critics,
    },
)

LOAD_ROUTER_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "b3_missing_file", "root_kind": "tmp", "exc_type": FileNotFoundError},
    {
        "case_id": "b4_non_dict_root",
        "root_kind": "tmp",
        "yaml_body": "- a\n- b\n",
        "exc_type": ValueError,
        "msg_contains": ("YAML root must be a mapping",),
    },
)

LOAD_ROUTER_FROM_YAML_WIRING_CASE: dict[str, Any] = {
    "case_id": "b5_path_wiring",
    "yaml_body": "version: 1\npairings:\n  planner:\n    - x\n",
}

PRODUCER_TAXONOMY_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_canonical_filter",
        "registry_kind": "canonical",
        "expected": frozenset(CANONICAL_PRODUCERS),
    },
    {
        "case_id": "c2_frozenset_immutable",
        "registry_kind": "canonical",
        "validate": _validate_c2_frozenset_immutable,
    },
    {"case_id": "c3_empty_registry", "registry_kind": "empty", "validate": _validate_c3_empty},
    {
        "case_id": "c4_all_critics",
        "registry_kind": "all_critics",
        "expected": frozenset(),
    },
    {
        "case_id": "c5_suffix_boundary",
        "registry_kind": "suffix_boundary",
        "validate": _validate_c5_suffix_boundary,
    },
    {
        "case_id": "c6_agent_evaluator",
        "registry_kind": "agent_evaluator",
        "validate": _validate_c6_agent_evaluator,
    },
)

LIFECYCLE_TAXONOMY_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d1_canonical_union",
        "registry_kind": "canonical",
        "router_kind": "canonical",
        "validate": _validate_d1_canonical,
    },
    {
        "case_id": "d2_sorted_idempotent",
        "registry_kind": "canonical",
        "router_kind": "canonical",
        "validate": _validate_d2_sorted_idempotent,
    },
    {
        "case_id": "d3_default_critics_fallback",
        "registry_kind": "unknown_producer",
        "router_kind": "empty",
        "expected": DEFAULT_CRITICS_FALLBACK_KEYS,
    },
    {
        "case_id": "d4_empty_producers",
        "registry_kind": "empty",
        "router_kind": "strict_mock",
        "validate": _validate_d4_empty_producers,
    },
    {
        "case_id": "d5a_cross_reference",
        "registry_kind": "cross_pair",
        "router_kind": "cross_pair",
        "expected": ["backend_writer", "planner"],
    },
    {
        "case_id": "d5b_external_critic",
        "registry_kind": "planner_only",
        "router_kind": "external_critic",
        "expected": ["external_critic_xyz", "planner"],
    },
)
