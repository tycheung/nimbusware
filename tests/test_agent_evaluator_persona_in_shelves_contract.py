"""``assert_agent_evaluator_persona_in_shelves`` wrapper-level coverage closure (fo84).

fo80, fo81, fo82, fo83 systematically pinned the wrapper-level / direct
contracts for 4 of the 5 pre-flight gates in
[`RunOrchestrator.create_run`](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
at pipeline.py:154-158:

* Gate 1 (``assert_known_workflow``): fo80 propagation trilogy.
* Gate 2 (``assert_bundle_catalog_maps_resolve``): fo82 3-axis
  wrapper + helper matrix + parity meta-contract.
* Gate 3 (``assert_persona_shelves_valid``): fo81 Part B 3-axis
  wrapper (accept + FNF + 4 VE).
* Gate 5 (``assert_taxonomy_keys_resolve``): fo81 Part A 2-axis
  direct (accept + KE).

Gate 4 (``assert_agent_evaluator_persona_in_shelves``) is the
outlier -- only 3 ad-hoc tests at
[test_extensions_yaml.py:145-182](d:\\Hermes\\tests\\test_extensions_yaml.py)
cover (reject unknown / accept default / skip disabled) and never
sweep-pinned. The wrapper has 7+ unpinned axes:

* Accept arm with **shelf-backed** persona_id (only reserved
  ``"default"`` was covered; the real ``commerce`` /
  ``backend_engineer`` shelf entries from
  [configs/personas/shelves.yaml](d:\\Hermes\\configs\\personas\\shelves.yaml)
  were untested).
* **Detailed reject message**:
  ``got 'X'; known=['backend_engineer', 'commerce']`` -- only
  ``match="agent_evaluator"`` was asserted.
* **Short-circuit on persona_id="default" when shelves.yaml is
  missing** -- proves the default-check at
  [ingress.py:40-41](d:\\Hermes\\packages\\hermes_orchestrator\\ingress.py)
  fires BEFORE PersonaShelf load at line 43.
* **FNF propagation**: missing shelves.yaml + non-default persona
  -> FileNotFoundError from ``load_yaml`` in
  ``PersonaShelf.__init__``.
* **load_yaml VE propagation**: scalar-root shelves.yaml ->
  ``ValueError "YAML root must be a mapping:"``.
* **Graceful-degradation friendly errors**: valid YAML mapping but
  missing / degraded ``business_area`` / ``development_role`` ->
  ``all_persona_ids()`` returns frozenset() / partial ->
  friendly ValueError with ``known=[]`` / partial list.
* **Workflow-profile-cascade no-op**: invalid ``workflow_profile``
  -> ``parse_agent_evaluator_workflow_block`` cascades to defaults
  (``enabled=False``) -> wrapper no-ops without touching shelves.

fo84 closes the gate-4 wrapper-level coverage gap via three parts:

* **Part A** locks the 6-axis direct contract (4 accept axes + 1
  detailed reject message + 1 default-short-circuit on missing
  shelves).
* **Part B** locks the shelves-load propagation + graceful-
  degradation matrix (2 load-failure axes + 3 friendly-degradation
  sub-cases with class + prefix + ``known=[...]`` fragment check).
* **Part C** locks the workflow-profile-cascade no-op uniformity
  (3 cascade triggers x bare-repo + with-shelves parity).

Cross-slice symmetry table (per-gate wrapper-level matrix):

| Slice    | Gate | Function                                       |
|----------|------|------------------------------------------------|
| fo80     | 1    | assert_known_workflow                          |
| fo82     | 2    | assert_bundle_catalog_maps_resolve             |
| fo81 PtB | 3    | assert_persona_shelves_valid                   |
| **fo84** | **4** | **assert_agent_evaluator_persona_in_shelves** |
| fo81 PtA | 5    | assert_taxonomy_keys_resolve                   |

fo84 completes the **full per-gate wrapper-level coverage matrix**.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from hermes_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REAL_PERSONAS_DIR = _REPO_ROOT / "configs" / "personas"

# Real shelf-backed persona ids from configs/personas/shelves.yaml.
_SHELF_BUSINESS_AREA = "commerce"
_SHELF_DEVELOPMENT_ROLE = "backend_engineer"

_VE_FRIENDLY_PREFIX = "agent_evaluator.persona_id must be 'default'"
_VE_LOAD_YAML_PREFIX = "YAML root must be a mapping:"


# Graceful-degradation cases: each tuple is
# (case_id, shelves_body, expected_known_list).
# ``all_persona_ids()`` at [personas.py:46-60] gracefully returns
# frozenset() / partial when entries are missing / wrong-type; the
# wrapper then raises the friendly ValueError with the resulting
# ``known`` list. The 3 sub-cases below cover:
# * no shelf keys -> known=[]
# * business_area: [] (empty list) -> known=['backend_engineer']
# * business_area: null -> known=['backend_engineer']
# (the null branch at personas.py:53 short-circuits to ``continue``)
_DEGRADATION_CASES: list[tuple[str, str, list[str]]] = [
    (
        "no_shelf_keys",
        "version: 1\n",
        [],
    ),
    (
        "empty_business_area",
        (
            "version: 1\n"
            "business_area: []\n"
            "development_role:\n  - id: backend_engineer\n    display_name: Backend\n"
        ),
        ["backend_engineer"],
    ),
    (
        "null_business_area",
        (
            "version: 1\n"
            "business_area: null\n"
            "development_role:\n  - id: backend_engineer\n    display_name: Backend\n"
        ),
        ["backend_engineer"],
    ),
]


def _write_workflow(
    repo: Path,
    name: str,
    *,
    enabled: bool,
    persona_id: str | None,
) -> None:
    """Write ``configs/workflows/{name}.yaml`` under tmp repo with an agent_evaluator block."""
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    persona_line = f"  persona_id: {persona_id}\n" if persona_id is not None else ""
    body = (
        "version: 1\n"
        "agent_evaluator:\n"
        f"  enabled: {'true' if enabled else 'false'}\n"
        f"{persona_line}"
    )
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def _copy_real_personas(tmp_repo: Path) -> None:
    """Mirror the real ``configs/personas`` directory under ``tmp_repo``.

    Copies both ``shelves.yaml`` and ``critique_pairings.yaml``; the wrapper only
    needs ``shelves.yaml`` but copying the directory wholesale matches the existing
    fixture pattern at [test_extensions_yaml.py:149](d:\\Hermes\\tests\\test_extensions_yaml.py).
    """
    shutil.copytree(_REAL_PERSONAS_DIR, tmp_repo / "configs" / "personas")


def _write_shelves(tmp_repo: Path, body: str) -> Path:
    """Overwrite ``tmp_repo/configs/personas/shelves.yaml`` with ``body``."""
    pdir = tmp_repo / "configs" / "personas"
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / "shelves.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_assert_agent_evaluator_persona_in_shelves_6_axis_direct_contract(
    tmp_path: Path,
) -> None:
    """6-axis direct contract: 4 accept + 1 detailed reject + 1 default-short-circuit.

    Extends the 3 ad-hoc tests at
    [test_extensions_yaml.py:145-182](d:\\Hermes\\tests\\test_extensions_yaml.py)
    by:

    * Adding 2 new accept axes for shelf-backed persona_ids
      (``commerce`` business_area + ``backend_engineer``
      development_role from the real
      [configs/personas/shelves.yaml](d:\\Hermes\\configs\\personas\\shelves.yaml)).
    * Re-asserting the existing 2 accept axes (disabled + reserved
      default) with stronger fixtures.
    * Asserting the **detailed** reject message includes
      ``got 'X'`` AND ``known=['backend_engineer', 'commerce']``
      (previously only ``match="agent_evaluator"`` was asserted).
    * Adding the **default-short-circuit** axis: persona_id=default
      + MISSING shelves.yaml returns None, proving the default
      check at [ingress.py:40-41](d:\\Hermes\\packages\\hermes_orchestrator\\ingress.py)
      fires BEFORE PersonaShelf load at line 43.
    """
    _copy_real_personas(tmp_path)

    _write_workflow(tmp_path, "disabled_with_garbage", enabled=False, persona_id="nope")
    assert (
        assert_agent_evaluator_persona_in_shelves(tmp_path, "disabled_with_garbage")
        is None
    ), "enabled=False with non-shelf persona_id must short-circuit BEFORE persona check"

    _write_workflow(tmp_path, "default_persona", enabled=True, persona_id="default")
    assert (
        assert_agent_evaluator_persona_in_shelves(tmp_path, "default_persona") is None
    ), "enabled=True + persona_id='default' must short-circuit on reserved-slug"

    _write_workflow(tmp_path, "shelf_commerce", enabled=True, persona_id=_SHELF_BUSINESS_AREA)
    assert (
        assert_agent_evaluator_persona_in_shelves(tmp_path, "shelf_commerce") is None
    ), f"shelf-backed business_area {_SHELF_BUSINESS_AREA!r} must be accepted"

    _write_workflow(
        tmp_path, "shelf_backend", enabled=True, persona_id=_SHELF_DEVELOPMENT_ROLE,
    )
    assert (
        assert_agent_evaluator_persona_in_shelves(tmp_path, "shelf_backend") is None
    ), f"shelf-backed development_role {_SHELF_DEVELOPMENT_ROLE!r} must be accepted"

    _write_workflow(
        tmp_path, "unknown_persona", enabled=True, persona_id="no_such_persona",
    )
    with pytest.raises(ValueError, match=re.escape(_VE_FRIENDLY_PREFIX)) as exc_info:
        assert_agent_evaluator_persona_in_shelves(tmp_path, "unknown_persona")
    msg = str(exc_info.value)
    assert "got 'no_such_persona'" in msg, (
        f"reject message {msg!r} missing got fragment"
    )
    assert "known=['backend_engineer', 'commerce']" in msg, (
        f"reject message {msg!r} missing sorted known-set fragment"
    )

    short_circuit_repo = tmp_path / "short_circuit"
    short_circuit_repo.mkdir()
    _write_workflow(
        short_circuit_repo, "default_no_shelves", enabled=True, persona_id="default",
    )
    assert (
        assert_agent_evaluator_persona_in_shelves(
            short_circuit_repo, "default_no_shelves",
        )
        is None
    ), (
        "persona_id='default' must short-circuit BEFORE shelves.yaml load; "
        "missing shelves.yaml should not raise on the reserved-default path"
    )


def test_assert_agent_evaluator_persona_in_shelves_shelves_load_and_degradation_matrix(
    tmp_path: Path,
) -> None:
    """Shelves-load propagation + graceful-degradation matrix.

    Two sub-loops:

    * **Sub-loop 1** -- shelves-load failures propagate uncaught.
      ``PersonaShelf.__init__`` at
      [personas.py:14-15](d:\\Hermes\\packages\\hermes_extensions\\personas.py)
      calls ``load_yaml(shelves_path)`` which raises FNF for
      missing files and ValueError for non-mapping roots; neither
      is caught by the wrapper.

    * **Sub-loop 2** -- graceful degradation when YAML root is a
      mapping but ``business_area`` / ``development_role`` entries
      are missing or wrong-type. ``all_persona_ids()`` at
      [personas.py:46-60](d:\\Hermes\\packages\\hermes_extensions\\personas.py)
      gracefully returns ``frozenset()`` / partial; the wrapper
      then raises the friendly ValueError with the resulting
      ``known`` list. 3 sub-cases pin the contract by asserting
      the ``known=[...]`` fragment appears verbatim in the message.
    """
    fnf_repo = tmp_path / "fnf"
    fnf_repo.mkdir()
    _write_workflow(fnf_repo, "fnf_wf", enabled=True, persona_id="some_id")
    with pytest.raises(FileNotFoundError):
        assert_agent_evaluator_persona_in_shelves(fnf_repo, "fnf_wf")

    ve_repo = tmp_path / "ve_scalar"
    ve_repo.mkdir()
    _write_workflow(ve_repo, "ve_wf", enabled=True, persona_id="some_id")
    _write_shelves(ve_repo, "scalar-not-a-mapping\n")
    with pytest.raises(ValueError, match=re.escape(_VE_LOAD_YAML_PREFIX)):
        assert_agent_evaluator_persona_in_shelves(ve_repo, "ve_wf")

    for case_id, shelves_body, expected_known in _DEGRADATION_CASES:
        case_repo = tmp_path / f"deg_{case_id}"
        case_repo.mkdir()
        _write_workflow(case_repo, "deg_wf", enabled=True, persona_id="not_in_shelves")
        _write_shelves(case_repo, shelves_body)
        with pytest.raises(
            ValueError, match=re.escape(_VE_FRIENDLY_PREFIX),
        ) as exc_info:
            assert_agent_evaluator_persona_in_shelves(case_repo, "deg_wf")
        msg = str(exc_info.value)
        expected_fragment = f"known={expected_known!r}"
        assert expected_fragment in msg, (
            f"case {case_id!r}: friendly reject msg {msg!r} missing {expected_fragment!r}"
        )


def test_assert_agent_evaluator_persona_in_shelves_workflow_cascade_no_op_uniformity(
    tmp_path: Path,
) -> None:
    """Workflow-profile-cascade no-op uniformity.

    ``parse_agent_evaluator_workflow_block`` at
    [workflow_agent_evaluator.py:28-35](d:\\Hermes\\packages\\hermes_orchestrator\\workflow_agent_evaluator.py)
    cascades to defaults (``enabled=False``) when
    ``workflow_profile_path`` raises FNF/OSError/ValueError or
    when ``load_yaml`` raises ValueError/OSError/UnicodeDecodeError.
    The wrapper then no-ops at
    [ingress.py:38-39](d:\\Hermes\\packages\\hermes_orchestrator\\ingress.py).

    This is the **structural complement** to Part B: where Part B
    pins that shelves-load failures DO propagate, Part C pins that
    workflow-load failures DO NOT propagate as gate-4 errors --
    the cascade-to-default fires BEFORE the PersonaShelf load.

    Two-stage assertion:

    1. **Bare-repo** (no shelves.yaml at all): if the cascade did
       NOT fire before the shelves load, FileNotFoundError would
       surface here. The fact that no exception is raised proves
       the cascade short-circuits at line 38-39.
    2. **With-shelves-repo**: same 3 cascade triggers on a repo
       that HAS valid shelves but no workflow files. Cross-layer
       parity: cascade still wins (shelves never read).
    """
    bare_repo = tmp_path / "bare"
    bare_repo.mkdir()

    # mypy: parse_agent_evaluator_workflow_block at line 25-26
    # explicitly handles None via str(workflow_profile).strip()
    # short-circuit (early-return BEFORE workflow_profile_path).
    # The wrapper signature declares ``str`` but the parser
    # accepts ``str | None``; mypy ignore matches the runtime path.
    assert (
        assert_agent_evaluator_persona_in_shelves(bare_repo, None)  # type: ignore[arg-type]
        is None
    )
    assert (
        assert_agent_evaluator_persona_in_shelves(bare_repo, "bad name") is None
    )
    assert (
        assert_agent_evaluator_persona_in_shelves(bare_repo, "does-not-exist") is None
    )

    with_shelves_repo = tmp_path / "with_shelves"
    with_shelves_repo.mkdir()
    _copy_real_personas(with_shelves_repo)
    for invalid_name in (None, "bad name", "does-not-exist"):
        assert (
            assert_agent_evaluator_persona_in_shelves(
                with_shelves_repo,
                invalid_name,  # type: ignore[arg-type]
            )
            is None
        ), (
            f"cascade-to-default no-op broken for workflow_profile={invalid_name!r}; "
            f"cascade should fire BEFORE shelves load (line 38-39 short-circuit)"
        )
