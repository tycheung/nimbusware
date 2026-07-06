from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from env import find_repo_root
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.routing import (
    default_critique_pairings_path,
    load_critique_router,
    registry_producer_taxonomy_keys,
    taxonomy_keys_for_run_lifecycle,
)
from orchestrator.registry import RoleRegistry
from unit.composite_contracts.critique_routing_matrix import (
    _ALL_CRITIC_REGISTRY,
    _SUFFIX_BOUNDARY_REGISTRY,
    LIFECYCLE_TAXONOMY_CASES,
    LOAD_ROUTER_EXCEPTION_CASES,
    LOAD_ROUTER_FROM_YAML_WIRING_CASE,
    LOAD_ROUTER_VALUE_CASES,
    PATH_COMPOSITION_CASES,
    PRODUCER_TAXONOMY_CASES,
)
from unit.composite_contracts.matrix_runner import run_exception_matrix, run_value_matrix
from unit.composite_orchestrator_fixtures import (
    canonical_critique_router,
    canonical_role_registry,
    deterministic_uuid,
)
from unit.composite_repo_fixtures import write_critique_pairings

_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def _resolve_root(case: dict[str, Any], tmp_path: Path) -> Path:
    kind = case["root_kind"]
    if kind == "repo":
        root = _REPO_ROOT
    elif kind == "ghost":
        root = tmp_path / "does" / "not" / "exist"
        case["ghost_root"] = root
    elif kind == "relative":
        root = case["relative_root"]
    else:
        root = tmp_path / case.get("case_id", "tmp")
        root.mkdir(parents=True, exist_ok=True)
    case["resolved_root"] = root
    return root


def _resolve_repo(case: dict[str, Any], tmp_path: Path) -> Path:
    repo = _resolve_root(case, tmp_path)
    if "yaml_body" in case:
        write_critique_pairings(repo, case["yaml_body"])
    return repo


def _registry_for(case: dict[str, Any]) -> RoleRegistry:
    kind = case["registry_kind"]
    if kind == "canonical":
        return canonical_role_registry()
    if kind == "empty":
        return RoleRegistry.from_mapping({})
    if kind == "all_critics":
        return RoleRegistry.from_mapping(_ALL_CRITIC_REGISTRY)
    if kind == "suffix_boundary":
        return RoleRegistry.from_mapping(_SUFFIX_BOUNDARY_REGISTRY)
    if kind == "agent_evaluator":
        return RoleRegistry.from_mapping(
            {
                "planner": deterministic_uuid(40),
                "agent_evaluator": deterministic_uuid(41),
                "product_reference_critic": deterministic_uuid(42),
            }
        )
    if kind == "unknown_producer":
        return RoleRegistry.from_mapping({"unknown_producer": deterministic_uuid(100)})
    if kind == "cross_pair":
        return RoleRegistry.from_mapping(
            {"planner": deterministic_uuid(40), "backend_writer": deterministic_uuid(41)}
        )
    if kind == "planner_only":
        return RoleRegistry.from_mapping({"planner": deterministic_uuid(50)})
    raise ValueError(f"unknown registry_kind: {kind!r}")


def _router_for(case: dict[str, Any]) -> UniversalCritiqueRouter | MagicMock:
    kind = case["router_kind"]
    if kind == "canonical":
        return canonical_critique_router()
    if kind == "empty":
        return UniversalCritiqueRouter({})
    if kind == "strict_mock":
        strict_router = MagicMock(spec=UniversalCritiqueRouter)
        strict_router.pairing_for.side_effect = RuntimeError(
            "pairing_for should NOT be called for empty producers"
        )
        case["strict_router"] = strict_router
        return strict_router
    if kind == "cross_pair":
        return UniversalCritiqueRouter(
            {"planner": ["backend_writer"], "backend_writer": ["planner"]}
        )
    if kind == "external_critic":
        return UniversalCritiqueRouter({"planner": ["external_critic_xyz"]})
    raise ValueError(f"unknown router_kind: {kind!r}")


def _invoke_path(case: dict[str, Any], tmp_path: Path) -> Path:
    return default_critique_pairings_path(_resolve_root(case, tmp_path))


def _invoke_load_router(case: dict[str, Any], tmp_path: Path) -> UniversalCritiqueRouter:
    router = load_critique_router(_resolve_repo(case, tmp_path))
    assert isinstance(router, UniversalCritiqueRouter)
    return router


def _invoke_producer_taxonomy(case: dict[str, Any]) -> frozenset[str]:
    return registry_producer_taxonomy_keys(_registry_for(case))


def _invoke_lifecycle_taxonomy(case: dict[str, Any]) -> list[str]:
    registry = _registry_for(case)
    router = _router_for(case)
    result = taxonomy_keys_for_run_lifecycle(registry, router)
    if case["case_id"] == "d2_sorted_idempotent":
        case["second_call"] = taxonomy_keys_for_run_lifecycle(registry, router)
    return result


@pytest.mark.parametrize("case", PATH_COMPOSITION_CASES, ids=lambda c: c["case_id"])
def test_default_path_composition_matrix(case: dict[str, Any], tmp_path: Path) -> None:
    run_value_matrix((case,), invoke=lambda c: _invoke_path(c, tmp_path))


@pytest.mark.parametrize("case", LOAD_ROUTER_VALUE_CASES, ids=lambda c: c["case_id"])
def test_load_critique_router_value_matrix(case: dict[str, Any], tmp_path: Path) -> None:
    run_value_matrix((case,), invoke=lambda c: _invoke_load_router(c, tmp_path))


@pytest.mark.parametrize("case", LOAD_ROUTER_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_load_critique_router_exception_matrix(case: dict[str, Any], tmp_path: Path) -> None:
    run_exception_matrix((case,), invoke=lambda c: load_critique_router(_resolve_repo(c, tmp_path)))


def test_load_critique_router_from_yaml_wiring(tmp_path: Path) -> None:
    case = LOAD_ROUTER_FROM_YAML_WIRING_CASE
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    write_critique_pairings(repo, case["yaml_body"])

    with patch.object(
        UniversalCritiqueRouter,
        "from_yaml",
        wraps=UniversalCritiqueRouter.from_yaml,
    ) as spy:
        router = load_critique_router(repo)

    assert spy.call_count == 1
    assert spy.call_args.args[0] == default_critique_pairings_path(repo)
    assert isinstance(router, UniversalCritiqueRouter)


@pytest.mark.parametrize("case", PRODUCER_TAXONOMY_CASES, ids=lambda c: c["case_id"])
def test_registry_producer_taxonomy_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_producer_taxonomy)


@pytest.mark.parametrize("case", LIFECYCLE_TAXONOMY_CASES, ids=lambda c: c["case_id"])
def test_taxonomy_keys_for_run_lifecycle_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_lifecycle_taxonomy)
