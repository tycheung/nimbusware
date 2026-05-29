"""Composite contract tests for critique_routing."""


from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.critique_routing import (
    default_critique_pairings_path,
    load_critique_router,
    registry_producer_taxonomy_keys,
    taxonomy_keys_for_run_lifecycle,
)
from hermes_orchestrator.registry import RoleRegistry

# Builder helpers (no fixtures beyond pytest built-ins)

# Real-repo workspace root (parent of `tests/`).
_REPO_ROOT = Path(__file__).resolve().parents[1]

# The canonical 5-role registry that matches `configs/roles.yaml`.
_CANONICAL_PRODUCERS = ("planner", "backend_writer", "test_writer")
_CANONICAL_CRITICS = ("product_reference_critic", "domain_critic")
_CANONICAL_DEFAULT_CRITICS = ("product_reference_critic", "domain_critic")


def _uuid(n: int) -> UUID:
    """Deterministic UUID for test fixtures (no real role IDs needed)."""
    return UUID(int=n)


def _canonical_registry() -> RoleRegistry:
    """Registry matching the real `configs/roles.yaml` keys."""
    return RoleRegistry.from_mapping(
        {
            "planner": _uuid(1),
            "backend_writer": _uuid(2),
            "test_writer": _uuid(3),
            "product_reference_critic": _uuid(4),
            "domain_critic": _uuid(5),
        }
    )


def _canonical_router() -> UniversalCritiqueRouter:
    """Router matching the real `configs/personas/critique_pairings.yaml`."""
    return UniversalCritiqueRouter(
        {
            "planner": list(_CANONICAL_CRITICS),
            "backend_writer": list(_CANONICAL_CRITICS),
            "test_writer": list(_CANONICAL_CRITICS),
        }
    )


# Part A -- default_critique_pairings_path path-composition matrix


class TestPartADefaultPathComposition:
    """Pure path-composition helper. No I/O. No normalisation."""

    def test_a1_return_type_is_pathlib_path(self) -> None:
        """A1: return type is ``pathlib.Path`` (NOT ``str``).

        Callers (e.g. ``UniversalCritiqueRouter.from_yaml``) rely on
        ``Path`` semantics (``/`` operator, ``read_text(...)``). A
        refactor to return a ``str`` would silently break those
        callers' ``Path``-only methods.
        """
        result = default_critique_pairings_path(_REPO_ROOT)
        assert isinstance(result, Path)
        # Also reject the looser "PurePath" -- the concrete platform
        # subclass (PosixPath / WindowsPath) is what callers expect.
        assert not isinstance(result, str)

    def test_a2_exact_three_segment_composition(self) -> None:
        """A2: ``{repo_root}/configs/personas/critique_pairings.yaml``.

        Pin both the equality with the canonical composition AND the
        last-three path components. A refactor that changed the
        intermediate directory (e.g. ``configs/critique`` instead of
        ``configs/personas``) would silently break config loading.
        """
        result = default_critique_pairings_path(_REPO_ROOT)
        assert (
            result
            == _REPO_ROOT / "configs" / "personas" / "critique_pairings.yaml"
        )
        assert result.parts[-3:] == (
            "configs",
            "personas",
            "critique_pairings.yaml",
        )

    def test_a3_suffix_is_yaml_not_yml(self) -> None:
        """A3: extension is ``.yaml`` (NOT ``.yml``).

        A refactor that wrote ``.yml`` (a common alternative) would
        silently mismatch the file on disk.
        """
        result = default_critique_pairings_path(_REPO_ROOT)
        assert result.suffix == ".yaml"
        assert result.name == "critique_pairings.yaml"
        # And NOT the alternative spelling.
        assert result.suffix != ".yml"

    def test_a4_pure_function_no_io(self, tmp_path: Path) -> None:
        """A4: no I/O -- accepts a non-existent ``repo_root``.

        The helper returns a valid ``Path`` instance even when the
        repo root does not exist on disk. A refactor that added an
        ``if not repo_root.is_dir(): raise`` would change the
        pure-function contract and break callers that build the path
        before creating the file.
        """
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
        """A5: no ``.resolve()`` / ``.absolute()`` normalisation.

        Whatever the caller passes flows through unchanged. Both
        absolute and relative roots produce results that match the
        canonical ``repo_root / "configs" / ...`` composition. Pins
        that the helper does NOT silently absolutize relative paths
        (which would break callers that intentionally use a relative
        cwd-anchored root).
        """
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


def _write_pairings_yaml(repo_root: Path, body: str) -> Path:
    """Create `<repo_root>/configs/personas/critique_pairings.yaml`."""
    pairings_dir = repo_root / "configs" / "personas"
    pairings_dir.mkdir(parents=True, exist_ok=True)
    pairings_path = pairings_dir / "critique_pairings.yaml"
    pairings_path.write_text(body, encoding="utf-8")
    return pairings_path


class TestPartBLoadCritiqueRouter:
    """YAML factory; exception passthrough; path-composition wiring."""

    def test_b1_real_repo_load_happy_path(self) -> None:
        """B1: loads against the actual ``configs/personas/critique_pairings.yaml``.

        Returns a ``UniversalCritiqueRouter`` whose ``pairing_for``
        for each canonical producer matches the canonical critics.
        Pins integration with the real shipped YAML.
        """
        router = load_critique_router(_REPO_ROOT)
        assert isinstance(router, UniversalCritiqueRouter)

        _repo_pairings = {
            "planner": _CANONICAL_CRITICS,
            "backend_writer": (
                "product_reference_critic",
                "domain_critic",
                "security_critic",
                "performance_critic",
                "network_resilience_critic",
            ),
            "test_writer": _CANONICAL_CRITICS,
        }
        for producer, expected in _repo_pairings.items():
            paired = router.pairing_for(producer)
            assert sorted(paired) == sorted(expected), (
                f"producer {producer!r} pairing drift"
            )

    def test_b2_empty_pairings_yaml_returns_empty_router(
        self, tmp_path: Path
    ) -> None:
        """B2: YAML without a ``pairings`` key -> empty router; default critics fall back.

        ``UniversalCritiqueRouter.from_yaml`` returns ``cls({})`` when
        the loaded mapping has no ``pairings`` key (or it's not a
        dict). Subsequent ``pairing_for("any-producer")`` then falls
        back to ``_DEFAULT_CRITICS``. Pins this combined contract.
        """
        _write_pairings_yaml(tmp_path, "version: 1\n")
        router = load_critique_router(tmp_path)
        assert isinstance(router, UniversalCritiqueRouter)

        # Any producer -> default critics fallback.
        for producer in ("any-producer", "planner", "unknown_role"):
            paired = router.pairing_for(producer)
            assert tuple(paired) == _CANONICAL_DEFAULT_CRITICS

    def test_b3_missing_file_propagates_filenotfounderror(
        self, tmp_path: Path
    ) -> None:
        """B3: KEY DIVERGENCE -- missing file -> ``FileNotFoundError`` propagates.

        ``load_critique_router`` does NOT wrap or swallow exceptions
        from ``UniversalCritiqueRouter.from_yaml`` / ``load_yaml``. A
        refactor that returned an empty router on missing file would
        silently mask deployment misconfiguration.
        """
        # tmp_path has NO configs/personas/critique_pairings.yaml.
        with pytest.raises(FileNotFoundError):
            load_critique_router(tmp_path)

    def test_b4_non_dict_yaml_root_propagates_valueerror(
        self, tmp_path: Path
    ) -> None:
        """B4: KEY DIVERGENCE -- non-dict YAML root -> ``ValueError`` propagates.

        ``load_yaml`` raises ``ValueError("YAML root must be a
        mapping: ...")`` when the YAML decodes to a non-dict (list,
        scalar, None). Pins that this propagates through
        ``load_critique_router`` instead of degrading to an empty
        router.
        """
        # List at root.
        _write_pairings_yaml(tmp_path, "- a\n- b\n")
        with pytest.raises(ValueError, match="YAML root must be a mapping"):
            load_critique_router(tmp_path)

    def test_b5_path_composition_wiring_via_from_yaml(
        self, tmp_path: Path
    ) -> None:
        """B5: ``load_critique_router`` passes the canonical path to ``from_yaml``.

        Pin that ``load_critique_router(repo_root)`` invokes
        ``UniversalCritiqueRouter.from_yaml`` with EXACTLY
        ``default_critique_pairings_path(repo_root)`` -- no extra
        wrapping, no path mutation. Uses ``patch.object`` with
        ``wraps=`` so the real factory still executes and the loaded
        YAML is still validated.
        """
        _write_pairings_yaml(tmp_path, "version: 1\npairings:\n  planner:\n    - x\n")

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
        """C1: KEY DIVERGENCE -- canonical filter on real repo roles.

        Registry with the 5 canonical roles (3 producers + 2 critics)
        -> output is exactly the 3 producers. A refactor to a
        different filter rule (e.g. allow-list of producer names)
        would either over- or under-filter.
        """
        result = registry_producer_taxonomy_keys(_canonical_registry())
        assert result == frozenset(_CANONICAL_PRODUCERS)

    def test_c2_return_type_is_frozenset_and_immutable(self) -> None:
        """C2: ``frozenset[str]`` return; immutable (no ``.add``).

        Callers may use the result as a dict key or stash it in a
        set; this requires hashability and immutability. A refactor
        to ``return {...}`` (set literal) would break both.
        """
        result = registry_producer_taxonomy_keys(_canonical_registry())
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
        """C4: every key ends in ``_critic`` -> empty ``frozenset()``.

        Pins that the filter actually drops ALL critic-suffixed keys,
        not just "some" -- a refactor with off-by-one or first-only
        filtering would still produce a non-empty set here.
        """
        all_critics = RoleRegistry.from_mapping(
            {
                "a_critic": _uuid(10),
                "b_critic": _uuid(11),
                "domain_critic": _uuid(12),
                "product_reference_critic": _uuid(13),
            }
        )
        result = registry_producer_taxonomy_keys(all_critics)
        assert result == frozenset()

    def test_c5_suffix_vs_substring_boundary_cases_key_divergence(self) -> None:
        """C5: KEY DIVERGENCE -- ``endswith`` is suffix-only, NOT substring.

        Build a registry where keys exercise the boundary between
        "ends with ``_critic``" (filtered) and "contains ``critic``
        but does not end with the suffix" (NOT filtered). A refactor
        from ``endswith("_critic")`` to ``"_critic" in k`` or
        ``"critic" in k`` would change behavior on every NOT-ends-with
        case.
        """
        registry = RoleRegistry.from_mapping(
            {
                # NOT filtered (no `_critic` suffix):
                "critic": _uuid(20),            # no underscore
                "critic_helper": _uuid(21),     # contains, not endswith
                "x_critic_y": _uuid(22),        # contains, not endswith
                "criticism_team": _uuid(23),    # different word entirely
                # Filtered (endswith `_critic`):
                "_critic": _uuid(30),           # bare suffix
                "super_critic": _uuid(31),
                "planner_critic": _uuid(32),
                "domain_critic": _uuid(33),
            }
        )
        result = registry_producer_taxonomy_keys(registry)
        assert result == frozenset(
            {"critic", "critic_helper", "x_critic_y", "criticism_team"}
        )
        # Cross-check: every filtered key has the suffix.
        for filtered_key in {"_critic", "super_critic", "planner_critic", "domain_critic"}:
            assert filtered_key not in result
            assert filtered_key.endswith("_critic")

    def test_c6_agent_evaluator_producer_excluded_from_lifecycle_accounting(self) -> None:
        """C6: ``agent_evaluator`` is excluded even when present in the registry.

        Lifecycle coverage snapshots must not treat optional evaluator producers
        as registry producers requiring critique pairings.
        """
        registry = RoleRegistry.from_mapping(
            {
                "planner": _uuid(40),
                "agent_evaluator": _uuid(41),
                "product_reference_critic": _uuid(42),
            }
        )
        result = registry_producer_taxonomy_keys(registry)
        assert "planner" in result
        assert "agent_evaluator" not in result


# Part D -- taxonomy_keys_for_run_lifecycle set-union + sorted matrix


class TestPartDLifecycleUnionSorted:
    """Set-union dedup, sorted-list contract, default-critics fallback."""

    def test_d1_canonical_set_union_dedup(self) -> None:
        """D1: KEY DIVERGENCE -- 5-role canonical layout produces 5 unique keys.

        The 3 producers each pair with the same 2 critics. Naive
        ``list.extend`` would produce 3 + 3*2 = 9 entries with
        duplicates; set-union dedup correctly yields 5 unique keys.
        """
        result = taxonomy_keys_for_run_lifecycle(
            _canonical_registry(), _canonical_router()
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
        """D2: KEY DIVERGENCE -- output is a sorted ``list[str]`` (not set).

        Output type is ``list[str]`` (NOT ``set`` / ``frozenset``).
        Stable alphabetical ordering across calls. Pins that callers
        downstream can rely on positional ordering (e.g. for
        diff-friendly snapshots).
        """
        registry = _canonical_registry()
        router = _canonical_router()

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
        """D3: KEY DIVERGENCE -- unpinned producer drags in default critics.

        Registry has a producer not present in any router pairing;
        the empty router falls back to ``_DEFAULT_CRITICS`` via
        ``pairing_for``, so the output includes both default critics
        PLUS the producer. A refactor that returned ``[]`` for
        unknown producers would silently drop default critic coverage
        for any newly-added producer role.
        """
        registry = RoleRegistry.from_mapping(
            {"unknown_producer": _uuid(100)}
        )
        empty_router = UniversalCritiqueRouter({})

        result = taxonomy_keys_for_run_lifecycle(registry, empty_router)
        assert result == [
            "domain_critic",
            "product_reference_critic",
            "unknown_producer",
        ]

    def test_d4_empty_producers_skips_pairing_for_entirely(self) -> None:
        """D4: empty producer set -> ``pairing_for`` is NEVER called.

        Pin via ``MagicMock`` router whose ``pairing_for`` raises if
        invoked. An empty registry produces an empty producer
        frozenset, so the for-loop body never executes and the mock
        is never touched. Pins the short-circuit semantics: a
        refactor that always called ``pairing_for("default")`` would
        fail this test.
        """
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
        """D5: KEY DIVERGENCE -- cross-reference dedup + external-pair inclusion.

        Two-arm test:

        (a) Two producers cross-reference each other via explicit
        router pairings: ``planner -> [backend_writer]`` AND
        ``backend_writer -> [planner]``. The output contains each
        ONCE despite each appearing in both the producer set AND a
        pairing list. A refactor to ``list.extend`` without dedup
        would produce duplicates.

        (b) A pairing contains a critic-name NOT in the registry.
        That external critic IS still included in the final output
        (the helper unions producers AND each pairing's keys,
        regardless of whether those keys exist in the registry).
        """
        # (a) Mutual cross-reference between two producers.
        cross_router = UniversalCritiqueRouter(
            {
                "planner": ["backend_writer"],
                "backend_writer": ["planner"],
            }
        )
        cross_registry = RoleRegistry.from_mapping(
            {"planner": _uuid(40), "backend_writer": _uuid(41)}
        )
        result_a = taxonomy_keys_for_run_lifecycle(cross_registry, cross_router)
        assert result_a == ["backend_writer", "planner"]
        assert len(result_a) == 2

        # (b) External critic name appearing only in pairings (not in registry).
        external_router = UniversalCritiqueRouter(
            {"planner": ["external_critic_xyz"]}
        )
        external_registry = RoleRegistry.from_mapping({"planner": _uuid(50)})
        result_b = taxonomy_keys_for_run_lifecycle(
            external_registry, external_router
        )
        assert result_b == ["external_critic_xyz", "planner"]
