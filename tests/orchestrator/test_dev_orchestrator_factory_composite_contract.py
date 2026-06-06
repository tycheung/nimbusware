"""default_paths`` + ``make_dev_orchestrator`` dev-factory composite."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import (
    RunOrchestrator,
    default_paths,
    make_dev_orchestrator,
)
from nimbusware_store.memory import InMemoryEventStore

# -- Part A -- ``default_paths`` shape + path-suffix wire-format (5 axes) ------


def test_default_paths_shape_and_suffix_wire_format_5_axis(tmp_path: Path) -> None:
    paths = default_paths()
    assert isinstance(paths, tuple), (
        f"A1: ``default_paths`` must return a ``tuple`` (callers do "
        f"tuple-unpack at e.g. [pipeline.py:1568]"
        f"(packages/nimbusware_orchestrator/pipeline.py) "
        f"``base, _ = default_paths(root)``); got {type(paths).__name__}"
    )
    assert len(paths) == 2, (
        f"A1: arity must be exactly 2 (model-routing + workflow-default); a "
        f"refactor that added a 3rd path (e.g. roles.yaml) would force every "
        f"caller using ``base, _ = ...`` to update -- pin the current arity. "
        f"Got len={len(paths)}: {paths!r}"
    )

    assert paths[0].name == "model-routing.yaml", (
        f"A2: first element must be the ``model-routing.yaml`` file (model "
        f"preflight / selection config). A refactor that swapped the two "
        f"paths would still pass A1 but break this axis. Got: {paths[0]!r}"
    )
    assert paths[0].parent.name == "configs", (
        f"A2: first element's immediate parent must be ``configs/`` "
        f"(NOT a deeper subdir like ``configs/models/``). Got parent: "
        f"{paths[0].parent.name!r} (full path {paths[0]!r})"
    )

    assert paths[1].name == "default.yaml", (
        f"A3: second element's filename must be ``default.yaml`` (workflow "
        f"profile). Got: {paths[1]!r}"
    )
    assert paths[1].parent.name == "workflows", (
        f"A3: second element's immediate parent must be ``workflows/`` "
        f"(distinguishing the workflow file from the model-routing one). "
        f"Got parent: {paths[1].parent.name!r} (full path {paths[1]!r})"
    )
    assert paths[1].parent.parent.name == "configs", (
        f"A3: second element's grandparent must be ``configs/`` (NOT a "
        f"sibling of ``configs/``). Got grandparent: "
        f"{paths[1].parent.parent.name!r} (full path {paths[1]!r})"
    )

    for idx, p in enumerate(paths):
        assert isinstance(p, Path), (
            f"A4: element {idx} must be a ``pathlib.Path`` (NOT ``str``) -- "
            f"a refactor that returned strings would still concatenate-compose "
            f"URLs but break downstream ``path.read_bytes()`` and "
            f"``path.parent`` operations used by ``RoleRegistry.from_yaml`` and "
            f"``RunOrchestrator._base_cfg()`` at "
            f"[pipeline.py:143-144](packages/nimbusware_orchestrator/pipeline.py). "
            f"Got type({idx})={type(p).__name__} value={p!r}"
        )

    paths_custom = default_paths(tmp_path)
    assert paths_custom[0].is_relative_to(tmp_path), (
        f"A5: first path must be a descendant of the supplied ``repo_root`` "
        f"override (so callers passing a custom root get a self-contained "
        f"path tree). Got: {paths_custom[0]!r} (root: {tmp_path!r})"
    )
    assert paths_custom[1].is_relative_to(tmp_path), (
        f"A5: second path must ALSO be a descendant of the supplied "
        f"``repo_root`` override (a refactor that honored the override on "
        f"only the first element would still produce a 2-tuple but the second "
        f"path would point into the FALLBACK ``parents[2]`` root -- silent "
        f"divergence across the two paths). Got: {paths_custom[1]!r} "
        f"(root: {tmp_path!r})"
    )
    assert paths_custom[0] == tmp_path / "configs" / "model-routing.yaml", (
        f"A5: first override path must be exactly "
        f"``<root>/configs/model-routing.yaml`` (pins that suffix is unchanged "
        f"under override). Got: {paths_custom[0]!r}"
    )
    assert paths_custom[1] == tmp_path / "configs" / "workflows" / "default.yaml", (
        f"A5: second override path must be exactly "
        f"``<root>/configs/workflows/default.yaml``. Got: {paths_custom[1]!r}"
    )


# -- Part B -- ``default_paths`` repo-root resolution (5 axes) -----------------


def test_default_paths_root_resolution_5_axis(tmp_path: Path) -> None:
    assert default_paths(None) == default_paths(), (
        f"B1: ``default_paths(None)`` must equal ``default_paths()`` "
        f"(no-arg). The parameter default is ``None`` and the ``or``-fallback "
        f"branches on truthiness -- ``None`` is falsy -> fallback. A refactor "
        f"that changed the default to a sentinel (e.g. ``MISSING`` object) "
        f"would break the ``None`` arm if the sentinel logic differed. "
        f"Got: {default_paths(None)!r} != {default_paths()!r}"
    )

    paths = default_paths()
    assert paths[0].is_absolute(), (
        f"B2: first path must be absolute -- ``Path(__file__).resolve()`` "
        f"guarantees absolute path. A refactor that dropped ``.resolve()`` "
        f"and used ``Path(__file__).parents[2]`` directly would yield a "
        f"path that's absolute on most installs but could be relative under "
        f"unusual import setups. Got: {paths[0]!r}"
    )
    assert paths[1].is_absolute(), f"B2: second path must also be absolute. Got: {paths[1]!r}"

    resolved_root = paths[0].parent.parent
    assert (resolved_root / "configs").is_dir(), (
        f"B3: resolved root must contain a ``configs/`` directory -- pins "
        f"that ``parents[2]`` is the CORRECT index for ``pipeline.py`` "
        f"located at ``packages/nimbusware_orchestrator/pipeline.py``. "
        f"``parents[1]`` would land in ``packages/`` (no ``configs/`` "
        f"sibling); ``parents[3]`` would land in the parent-of-repo (no "
        f"``configs/`` child of THE repo). A refactor that drifted the index "
        f"would silently break every default-root caller. Resolved root: "
        f"{resolved_root!r}"
    )
    assert (resolved_root / "packages" / "nimbusware_orchestrator" / "pipeline.py").is_file(), (
        f"B3: as a paired sanity check, the resolved root must contain "
        f"``packages/nimbusware_orchestrator/pipeline.py`` (the source of the "
        f"helper). Pins that ``parents[2]`` of ``pipeline.py`` IS the repo "
        f"root (NOT the package or the parent-of-repo). Resolved root: "
        f"{resolved_root!r}"
    )

    fresh_root = tmp_path / "no_such_root"
    assert not fresh_root.exists(), (
        f"B4 setup: ``tmp_path/no_such_root`` must NOT exist (pytest's "
        f"``tmp_path`` is fresh per test; we never create the subdir). "
        f"Got exists={fresh_root.exists()} at {fresh_root!r}"
    )
    paths_pure = default_paths(fresh_root)
    assert paths_pure[0] == fresh_root / "configs" / "model-routing.yaml", (
        f"B4: ``default_paths`` is PURE path composition -- it does NOT "
        f"call ``is_file()`` / ``read_bytes()`` / ``resolve()`` on the "
        f"composed paths. Passing a nonexistent root must NOT raise. A "
        f"refactor that added ``raise FileNotFoundError(...)`` guards "
        f"would break this. Got: {paths_pure[0]!r}"
    )
    assert paths_pure[1] == fresh_root / "configs" / "workflows" / "default.yaml", (
        f"B4: second pure-composition path must also anchor under the "
        f"nonexistent root. Got: {paths_pure[1]!r}"
    )

    assert paths[0].parent.parent == resolved_root, (
        f"B5: ``default_paths()[0].parent.parent`` must equal the resolved "
        f"root -- this is the structural invariant that ``make_dev_orchestrator`` "
        f"would rely on if it derived the root from the returned tuple "
        f"(see D2). The chain is: ``configs/model-routing.yaml`` -> "
        f"``configs/`` -> ``<root>``. Got: parent.parent={paths[0].parent.parent!r} "
        f"vs resolved_root={resolved_root!r}"
    )
    assert paths[1].parent.parent.parent == resolved_root, (
        f"B5: ``default_paths()[1].parent.parent.parent`` must also equal "
        f"the resolved root. The chain is: ``configs/workflows/default.yaml`` "
        f"-> ``configs/workflows/`` -> ``configs/`` -> ``<root>`` (one extra "
        f"hop vs the first path because of the ``workflows/`` subdir). A "
        f"refactor moving ``default.yaml`` up one level (out of ``workflows/``) "
        f"would break this. Got: parent.parent.parent={paths[1].parent.parent.parent!r} "
        f"vs resolved_root={resolved_root!r}"
    )


# -- Part C -- ``make_dev_orchestrator`` return shape + wiring (5 axes) --------


def test_make_dev_orchestrator_shape_and_wiring_5_axis() -> None:
    result = make_dev_orchestrator()
    assert isinstance(result, tuple) and len(result) == 2, (
        f"C1: ``make_dev_orchestrator`` must return a 2-tuple -- callers "
        f"across 30+ test files use ``orch, mem = make_dev_orchestrator()`` "
        f"tuple-unpack. A refactor returning a single object (e.g. a "
        f"dataclass) or a 3-tuple (e.g. adding the registry) would break "
        f"every caller. Got: type={type(result).__name__} value={result!r}"
    )

    orch, mem = result
    assert isinstance(orch, RunOrchestrator), (
        f"C2: first element must be an instance of ``RunOrchestrator`` "
        f"(NOT a subclass-replaced mock or a dict). Got: "
        f"type={type(orch).__name__}"
    )

    assert isinstance(mem, InMemoryEventStore), (
        f"C3: second element must be an instance of ``InMemoryEventStore`` "
        f"(NOT a generic ``EventStore`` protocol or a Postgres adapter). "
        f"The dev factory's WHOLE PURPOSE is to return the in-memory variant "
        f"-- a refactor to ``store = PostgresEventStore(...)`` would silently "
        f"hit the network in unit tests. Got: type={type(mem).__name__}"
    )

    expected_root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert orch.repo_root == expected_root, (
        f"C4: ``orch.repo_root`` must be wired through to the same root "
        f"that the factory resolves (``Path(<pipeline.py>).resolve().parents[2]`` "
        f"== ``Path(<this test file>).resolve().parents[1]`` since both "
        f"resolve to the repo root). A refactor that dropped the ``repo_root=root`` "
        f"kwarg from the ``RunOrchestrator(...)`` call would break this -- "
        f"``RunOrchestrator.__init__`` would then raise ``TypeError`` (required "
        f"kwarg), but a default-arg refactor on the constructor could mask "
        f"the wire-through silently. Got: orch.repo_root={orch.repo_root!r} "
        f"vs expected={expected_root!r}"
    )

    orch2, mem2 = make_dev_orchestrator()
    assert mem is not mem2, (
        f"C5: two separate factory calls must return DISTINCT "
        f"``InMemoryEventStore`` instances -- a refactor that hoisted "
        f"``_GLOBAL_MEM = InMemoryEventStore()`` to module scope (perhaps "
        f"to reuse the store across calls) would silently leak events "
        f"between tests, causing flaky test ordering. Got: id(mem)={id(mem)} "
        f"id(mem2)={id(mem2)} -- same object: {mem is mem2}"
    )
    assert orch is not orch2, (
        f"C5: similarly, distinct ``RunOrchestrator`` instances across calls. "
        f"id(orch)={id(orch)} id(orch2)={id(orch2)}"
    )
    assert mem._rows == [] and mem2._rows == [], (
        f"C5: each returned store must start with an EMPTY row list (no "
        f"events leaked from prior calls). Got: mem._rows={mem._rows!r} "
        f"mem2._rows={mem2._rows!r}"
    )
    assert mem._seq == 0 and mem2._seq == 0, (
        f"C5: each returned store's sequence counter must start at 0 (no "
        f"leaked seq state). Got: mem._seq={mem._seq} mem2._seq={mem2._seq}"
    )


# -- Part D -- cross-helper KEY DIVERGENCES + invariants (5 axes) --------------


def test_factory_cross_helper_key_divergences_5_axis(tmp_path: Path) -> None:
    orch, _mem = make_dev_orchestrator()
    paths = default_paths()
    assert orch._base_path == paths[0], (
        f"D1 KEY DIVERGENCE: ``make_dev_orchestrator`` unpacks "
        f"``base, _ = default_paths(root)`` at [pipeline.py:1568]"
        f"(packages/nimbusware_orchestrator/pipeline.py) -- the FIRST path "
        f"(``model-routing.yaml``) becomes ``base``, NOT the second. A "
        f"refactor swapping to ``_, base = ...`` or ``*_, base = ...`` "
        f"would silently wire ``RunOrchestrator(base_config_path=...)`` "
        f"to ``workflows/default.yaml`` -- the WRONG file -- and "
        f"``orch._base_cfg()`` at [pipeline.py:143-144]"
        f"(packages/nimbusware_orchestrator/pipeline.py) would load workflow "
        f"YAML when the orchestrator expected model-routing YAML. Got: "
        f"orch._base_path={orch._base_path!r} vs default_paths()[0]={paths[0]!r}"
    )
    assert orch._base_path != paths[1], (
        f"D1 KEY DIVERGENCE: ``orch._base_path`` must NOT equal "
        f"``default_paths()[1]`` (the workflow-default path). Pins that "
        f"the swap-unpacking refactor would be DETECTABLE -- since the "
        f"two paths are distinct (different filename + different parent), "
        f"a swap would flip this assertion. Got: "
        f"orch._base_path={orch._base_path!r} default_paths()[1]={paths[1]!r}"
    )

    via_first = paths[0].parent.parent
    via_second = paths[1].parent.parent.parent
    assert orch.repo_root == via_first, (
        f"D2 KEY DIVERGENCE: ``make_dev_orchestrator`` re-computes "
        f"``Path(__file__).resolve().parents[2]`` independently at "
        f"[pipeline.py:1567](packages/nimbusware_orchestrator/pipeline.py) "
        f"rather than delegating to ``default_paths(None)`` and walking "
        f"back via ``.parent.parent``. The two sites MUST agree. Pin via "
        f"``orch.repo_root == default_paths()[0].parent.parent``. A refactor "
        f"drifting the ``parents[N]`` index in EITHER site (e.g. "
        f"``parents[3]`` because of a directory rename) would break this. "
        f"Got: orch.repo_root={orch.repo_root!r} via_first={via_first!r}"
    )
    assert orch.repo_root == via_second, (
        f"D2 KEY DIVERGENCE: also pin agreement starting from the SECOND "
        f"path -- ``default_paths()[1].parent.parent.parent`` (one extra "
        f"hop because of the ``workflows/`` subdir) must yield the SAME "
        f"root. If only one of the two yielded the right root, the helpers "
        f"would silently diverge. Got: orch.repo_root={orch.repo_root!r} "
        f"via_second={via_second!r}"
    )
    assert via_first == via_second, (
        f"D2 KEY DIVERGENCE: ``default_paths``'s two return values must "
        f"BOTH be anchored under the SAME root (consistency invariant of "
        f"``default_paths`` itself, independent of ``make_dev_orchestrator``). "
        f"Got: via_first={via_first!r} via_second={via_second!r}"
    )

    paths_str = [str(p) for p in paths]
    assert all("roles.yaml" not in s for s in paths_str), (
        f"D3 KEY DIVERGENCE: ``roles.yaml`` is the THIRD hardcoded path at "
        f"[pipeline.py:1569](packages/nimbusware_orchestrator/pipeline.py) "
        f"(``RoleRegistry.from_yaml(root / 'configs' / 'roles.yaml')``) "
        f"and is NOT included in ``default_paths``'s 2-tuple. A refactor "
        f"that broadened ``default_paths`` to a 3-tuple including "
        f"``roles.yaml`` would still need to update the factory's "
        f"consumption (``base, _ = ...`` becomes ``base, _, _ = ...``) -- "
        f"pin the current separation. Got paths: {paths_str!r}"
    )
    expected_roles_path = via_first / "configs" / "roles.yaml"
    assert expected_roles_path.is_file(), (
        f"D3 paired sanity: the third hardcoded path "
        f"``<root>/configs/roles.yaml`` must actually exist in the real "
        f"repo (else ``make_dev_orchestrator()`` in Part C would have "
        f"raised). Pins that the third hardcoded location is correct and "
        f"the real repo has a roles file there. Got: {expected_roles_path!r}"
    )

    fresh_root = tmp_path / "no_such_root"
    assert not fresh_root.exists(), (
        f"D4 setup: ``tmp_path/no_such_root`` must NOT exist. Got exists={fresh_root.exists()}"
    )
    paths_ne = default_paths(fresh_root)
    assert paths_ne[0] == fresh_root / "configs" / "model-routing.yaml", (
        f"D4 KEY DIVERGENCE: ``default_paths`` is PURE path composition -- "
        f"passing a nonexistent root does NOT raise. Pin that the returned "
        f"path is correctly anchored under the nonexistent root. Pair this "
        f"axis with D5 (same nonexistent root, factory DOES raise) to pin "
        f"the asymmetry between the pure and impure helpers. Got: "
        f"{paths_ne[0]!r}"
    )
    assert not paths_ne[0].exists(), (
        f"D4: the returned path under the nonexistent root must NOT exist "
        f"on disk (sanity check that pure composition doesn't accidentally "
        f"create the file). Got: exists={paths_ne[0].exists()}"
    )

    with pytest.raises(FileNotFoundError) as exc_d5:
        make_dev_orchestrator(fresh_root)
    assert "roles.yaml" in str(exc_d5.value), (
        f"D5 KEY DIVERGENCE: ``make_dev_orchestrator(nonexistent_root)`` "
        f"MUST raise ``FileNotFoundError`` -- the impure helper reads "
        f"``roles.yaml`` via ``RoleRegistry.from_yaml(...).read_bytes()`` "
        f"at [pipeline.py:1569](packages/nimbusware_orchestrator/pipeline.py) / "
        f"[registry.py:26](packages/nimbusware_orchestrator/registry.py). "
        f"The error message must mention ``roles.yaml`` (pins that "
        f"``roles.yaml`` -- NOT ``model-routing.yaml`` or ``default.yaml`` "
        f"-- is the first file hit). A refactor that swapped the I/O order "
        f"(e.g. loaded ``base`` config first via "
        f"``RunOrchestrator._base_cfg()`` lazily) would still raise "
        f"``FileNotFoundError`` but mention a DIFFERENT file. Got: "
        f"{str(exc_d5.value)!r}"
    )
