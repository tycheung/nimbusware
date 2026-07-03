from __future__ import annotations

from pathlib import Path
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
from unit.composite_orchestrator_fixtures import (
    CANONICAL_CRITICS,
    CANONICAL_DEFAULT_CRITICS,
    CANONICAL_PRODUCERS,
    canonical_critique_router,
    canonical_role_registry,
    deterministic_uuid,
)
from unit.composite_repo_fixtures import write_critique_pairings

# Builder helpers (no fixtures beyond pytest built-ins)

# Real-repo workspace root (parent of `tests/`).
_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


# Part A -- default_critique_pairings_path path-composition matrix


class TestPartADefaultPathComposition:
    """Pure path-composition helper. No I/O. No normalisation."""

    def test_a1_return_type_is_pathlib_path(self) -> None:
        result = default_critique_pairings_path(_REPO_ROOT)
        assert isinstance(result, Path)
        # Also reject the looser "PurePath" -- the concrete platform
        # subclass (PosixPath / WindowsPath) is what callers expect.
        assert not isinstance(result, str)

    def test_a2_exact_three_segment_composition(self) -> None:
        result = default_critique_pairings_path(_REPO_ROOT)
        assert result == _REPO_ROOT / "configs" / "personas" / "critique_pairings.yaml"
        assert result.parts[-3:] == (
            "configs",
            "personas",
            "critique_pairings.yaml",
        )

    def test_a3_suffix_is_yaml_not_yml(self) -> None:
        result = default_critique_pairings_path(_REPO_ROOT)
        assert result.suffix == ".yaml"
        assert result.name == "critique_pairings.yaml"
        # And NOT the alternative spelling.
        assert result.suffix != ".yml"

    def test_a4_pure_function_no_io(self, tmp_path: Path) -> None:
        ghost = tmp_path / "does" / "not" / "exist"
        assert not ghost.exists()

        result = default_critique_pairings_path(ghost)
        # No raise, valid Path returned.
        assert isinstance(result, Path)
        # The composed file also doesn't exist (no implicit creation).
        assert not result.exists()
        # And the composed path includes the non-existent root verbatim.
        assert result.parent.parent.parent == ghost

    def test_a5_absolute_and_relative_roots_flow_through_unchanged(self) -> None:
        # Absolute (use a real OS-absolute path: C: drive on Windows,
        # / on POSIX. Both Path("/abs") on POSIX and Path("C:/abs") on
        # Windows are absolute. Use _REPO_ROOT which is guaranteed
        # absolute on either platform.)
        abs_root = _REPO_ROOT
        assert abs_root.is_absolute()
        abs_result = default_critique_pairings_path(abs_root)
        assert abs_result.is_absolute()
        assert abs_result == abs_root / "configs" / "personas" / "critique_pairings.yaml"

        # Relative (no normalisation -- relative stays relative).
        rel_root = Path("rel/y")
        assert not rel_root.is_absolute()
        rel_result = default_critique_pairings_path(rel_root)
        assert not rel_result.is_absolute()
        assert rel_result == rel_root / "configs" / "personas" / "critique_pairings.yaml"


# Part B -- load_critique_router YAML factory matrix


class TestPartBLoadCritiqueRouter:
    """YAML factory; exception passthrough; path-composition wiring."""

    def test_b1_real_repo_load_happy_path(self) -> None:
        router = load_critique_router(_REPO_ROOT)
        assert isinstance(router, UniversalCritiqueRouter)

        _repo_pairings = {
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
        for producer, expected in _repo_pairings.items():
            paired = router.pairing_for(producer)
            assert sorted(paired) == sorted(expected), f"producer {producer!r} pairing drift"

    def test_b2_empty_pairings_yaml_returns_empty_router(self, tmp_path: Path) -> None:
        write_critique_pairings(tmp_path, "version: 1\n")
        router = load_critique_router(tmp_path)
        assert isinstance(router, UniversalCritiqueRouter)

        # Any producer -> default critics fallback.
        for producer in ("any-producer", "planner", "unknown_role"):
            paired = router.pairing_for(producer)
            assert tuple(paired) == CANONICAL_DEFAULT_CRITICS

    def test_b3_missing_file_propagates_filenotfounderror(self, tmp_path: Path) -> None:
        # tmp_path has NO configs/personas/critique_pairings.yaml.
        with pytest.raises(FileNotFoundError):
            load_critique_router(tmp_path)

    def test_b4_non_dict_yaml_root_propagates_valueerror(self, tmp_path: Path) -> None:
        # List at root.
        write_critique_pairings(tmp_path, "- a\n- b\n")
        with pytest.raises(ValueError, match="YAML root must be a mapping"):
            load_critique_router(tmp_path)

    def test_b5_path_composition_wiring_via_from_yaml(self, tmp_path: Path) -> None:
        write_critique_pairings(tmp_path, "version: 1\npairings:\n  planner:\n    - x\n")

        with patch.object(
            UniversalCritiqueRouter,
            "from_yaml",
            wraps=UniversalCritiqueRouter.from_yaml,
        ) as spy:
            router = load_critique_router(tmp_path)

        assert spy.call_count == 1
        # Exactly the canonical-path argument.
        called_path = spy.call_args.args[0]
        expected_path = default_critique_pairings_path(tmp_path)
        assert called_path == expected_path
        # And the result is still a real router (wraps preserved behavior).
        assert isinstance(router, UniversalCritiqueRouter)


# Part C -- registry_producer_taxonomy_keys _critic suffix filter matrix


class TestPartCProducerSuffixFilter:
    """``endswith("_critic")`` filter and immutable frozenset return."""

    def test_c1_canonical_filter_drops_critic_suffixed_keys(self) -> None:
        result = registry_producer_taxonomy_keys(canonical_role_registry())
        assert result == frozenset(CANONICAL_PRODUCERS)

    def test_c2_return_type_is_frozenset_and_immutable(self) -> None:
        result = registry_producer_taxonomy_keys(canonical_role_registry())
        assert type(result) is frozenset

        # Immutable: frozenset has no `.add` method at all.
        with pytest.raises(AttributeError):
            result.add("x")  # type: ignore[attr-defined]

        # Hashable: can be used as a dict key.
        canary = {result: "ok"}
        assert canary[result] == "ok"

    def test_c3_empty_registry_returns_empty_frozenset(self) -> None:
        """C3: ``RoleRegistry.from_mapping({})`` -> empty ``frozenset()``.

        Pins the never-iterate-the-comprehension branch.
        """
        result = registry_producer_taxonomy_keys(RoleRegistry.from_mapping({}))
        assert result == frozenset()
        assert len(result) == 0
        assert type(result) is frozenset

    def test_c4_all_critic_registry_returns_empty_frozenset(self) -> None:
        all_critics = RoleRegistry.from_mapping(
            {
                "a_critic": deterministic_uuid(10),
                "b_critic": deterministic_uuid(11),
                "domain_critic": deterministic_uuid(12),
                "product_reference_critic": deterministic_uuid(13),
            }
        )
        result = registry_producer_taxonomy_keys(all_critics)
        assert result == frozenset()

    def test_c5_suffix_vs_substring_boundary_cases_key_divergence(self) -> None:
        registry = RoleRegistry.from_mapping(
            {
                # NOT filtered (no `_critic` suffix):
                "critic": deterministic_uuid(20),  # no underscore
                "critic_helper": deterministic_uuid(21),  # contains, not endswith
                "x_critic_y": deterministic_uuid(22),  # contains, not endswith
                "criticism_team": deterministic_uuid(23),  # different word entirely
                # Filtered (endswith `_critic`):
                "_critic": deterministic_uuid(30),  # bare suffix
                "super_critic": deterministic_uuid(31),
                "planner_critic": deterministic_uuid(32),
                "domain_critic": deterministic_uuid(33),
            }
        )
        result = registry_producer_taxonomy_keys(registry)
        assert result == frozenset({"critic", "critic_helper", "x_critic_y", "criticism_team"})
        # Cross-check: every filtered key has the suffix.
        for filtered_key in {"_critic", "super_critic", "planner_critic", "domain_critic"}:
            assert filtered_key not in result
            assert filtered_key.endswith("_critic")

    def test_c6_agent_evaluator_producer_excluded_from_lifecycle_accounting(self) -> None:
        registry = RoleRegistry.from_mapping(
            {
                "planner": deterministic_uuid(40),
                "agent_evaluator": deterministic_uuid(41),
                "product_reference_critic": deterministic_uuid(42),
            }
        )
        result = registry_producer_taxonomy_keys(registry)
        assert "planner" in result
        assert "agent_evaluator" not in result


# Part D -- taxonomy_keys_for_run_lifecycle set-union + sorted matrix


class TestPartDLifecycleUnionSorted:
    """Set-union dedup, sorted-list contract, default-critics fallback."""

    def test_d1_canonical_set_union_dedup(self) -> None:
        result = taxonomy_keys_for_run_lifecycle(
            canonical_role_registry(), canonical_critique_router()
        )
        assert result == [
            "backend_writer",
            "domain_critic",
            "planner",
            "product_reference_critic",
            "test_writer",
        ]
        # Each appears exactly once (no duplicates).
        assert len(result) == len(set(result)) == 5

    def test_d2_sorted_list_contract_and_idempotent(self) -> None:
        registry = canonical_role_registry()
        router = canonical_critique_router()

        result_a = taxonomy_keys_for_run_lifecycle(registry, router)
        result_b = taxonomy_keys_for_run_lifecycle(registry, router)

        # Type contract: list, not set.
        assert type(result_a) is list
        assert not isinstance(result_a, (set, frozenset))

        # Sorted: equal to its own sorted form.
        assert result_a == sorted(result_a)
        # Sorted explicitly removes duplicates step: pin via sorted(set(...))
        assert result_a == sorted(set(result_a))

        # Idempotent: two consecutive calls produce identical lists.
        assert result_a == result_b

    def test_d3_default_critics_fallback_for_unpinned_producer(self) -> None:
        registry = RoleRegistry.from_mapping({"unknown_producer": deterministic_uuid(100)})
        empty_router = UniversalCritiqueRouter({})

        result = taxonomy_keys_for_run_lifecycle(registry, empty_router)
        assert result == [
            "domain_critic",
            "product_reference_critic",
            "unknown_producer",
        ]

    def test_d4_empty_producers_skips_pairing_for_entirely(self) -> None:
        empty_registry = RoleRegistry.from_mapping({})
        strict_router = MagicMock(spec=UniversalCritiqueRouter)
        strict_router.pairing_for.side_effect = RuntimeError(
            "pairing_for should NOT be called for empty producers"
        )

        result = taxonomy_keys_for_run_lifecycle(empty_registry, strict_router)

        assert result == []
        assert strict_router.pairing_for.called is False
        assert strict_router.pairing_for.call_count == 0

    def test_d5_cross_reference_dedup_key_divergence(self) -> None:
        # (a) Mutual cross-reference between two producers.
        cross_router = UniversalCritiqueRouter(
            {
                "planner": ["backend_writer"],
                "backend_writer": ["planner"],
            }
        )
        cross_registry = RoleRegistry.from_mapping(
            {"planner": deterministic_uuid(40), "backend_writer": deterministic_uuid(41)}
        )
        result_a = taxonomy_keys_for_run_lifecycle(cross_registry, cross_router)
        assert result_a == ["backend_writer", "planner"]
        assert len(result_a) == 2

        # (b) External critic name appearing only in pairings (not in registry).
        external_router = UniversalCritiqueRouter({"planner": ["external_critic_xyz"]})
        external_registry = RoleRegistry.from_mapping({"planner": deterministic_uuid(50)})
        result_b = taxonomy_keys_for_run_lifecycle(external_registry, external_router)
        assert result_b == ["external_critic_xyz", "planner"]
