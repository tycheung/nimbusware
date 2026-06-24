from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves
from unit.composite_repo_fixtures import (
    write_agent_evaluator_workflow_profile,
    write_persona_shelves,
)

_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
_REAL_PERSONAS_DIR = _REPO_ROOT / "configs" / "personas"

# Real shelf-backed persona ids from configs/personas/shelves.yaml.
_SHELF_BUSINESS_AREA = "commerce"
_SHELF_DEVELOPMENT_ROLE = "backend_engineer"

_VE_FRIENDLY_PREFIX = "agent_evaluator.persona_id must be 'default'"
_VE_LOAD_YAML_PREFIX = "YAML root must be a mapping:"


# Graceful-degradation cases: each tuple is
# (case_id, shelves_body, expected_known_list).
# ``all_persona_ids`` at [personas.py:46-60] gracefully returns
# frozenset / partial when entries are missing / wrong-type; the
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


def _copy_real_personas(tmp_repo: Path) -> None:
    """Mirror the real ``configs/personas`` directory under ``tmp_repo``.

    Copies both ``shelves.yaml`` and ``critique_pairings.yaml``; the wrapper only
    needs ``shelves.yaml`` but copying the directory wholesale matches the existing
    fixture pattern at [test_extensions_yaml.py:149](tests\\test_extensions_yaml.py).
    """
    shutil.copytree(_REAL_PERSONAS_DIR, tmp_repo / "configs" / "personas")


def test_assert_agent_evaluator_persona_in_shelves_6_axis_direct_contract(
    tmp_path: Path,
) -> None:
    _copy_real_personas(tmp_path)

    write_agent_evaluator_workflow_profile(
        tmp_path, "disabled_with_garbage", enabled=False, persona_id="nope"
    )
    assert assert_agent_evaluator_persona_in_shelves(tmp_path, "disabled_with_garbage") is None, (
        "enabled=False with non-shelf persona_id must short-circuit BEFORE persona check"
    )

    write_agent_evaluator_workflow_profile(
        tmp_path, "default_persona", enabled=True, persona_id="default"
    )
    assert assert_agent_evaluator_persona_in_shelves(tmp_path, "default_persona") is None, (
        "enabled=True + persona_id='default' must short-circuit on reserved-slug"
    )

    write_agent_evaluator_workflow_profile(
        tmp_path, "shelf_commerce", enabled=True, persona_id=_SHELF_BUSINESS_AREA
    )
    assert assert_agent_evaluator_persona_in_shelves(tmp_path, "shelf_commerce") is None, (
        f"shelf-backed business_area {_SHELF_BUSINESS_AREA!r} must be accepted"
    )

    write_agent_evaluator_workflow_profile(
        tmp_path,
        "shelf_backend",
        enabled=True,
        persona_id=_SHELF_DEVELOPMENT_ROLE,
    )
    assert assert_agent_evaluator_persona_in_shelves(tmp_path, "shelf_backend") is None, (
        f"shelf-backed development_role {_SHELF_DEVELOPMENT_ROLE!r} must be accepted"
    )

    write_agent_evaluator_workflow_profile(
        tmp_path,
        "unknown_persona",
        enabled=True,
        persona_id="no_such_persona",
    )
    with pytest.raises(ValueError, match=re.escape(_VE_FRIENDLY_PREFIX)) as exc_info:
        assert_agent_evaluator_persona_in_shelves(tmp_path, "unknown_persona")
    msg = str(exc_info.value)
    assert "got 'no_such_persona'" in msg, f"reject message {msg!r} missing got fragment"
    assert "known=['backend_engineer', 'commerce']" in msg, (
        f"reject message {msg!r} missing sorted known-set fragment"
    )

    short_circuit_repo = tmp_path / "short_circuit"
    short_circuit_repo.mkdir()
    write_agent_evaluator_workflow_profile(
        short_circuit_repo,
        "default_no_shelves",
        enabled=True,
        persona_id="default",
    )
    assert (
        assert_agent_evaluator_persona_in_shelves(
            short_circuit_repo,
            "default_no_shelves",
        )
        is None
    ), (
        "persona_id='default' must short-circuit BEFORE shelves.yaml load; "
        "missing shelves.yaml should not raise on the reserved-default path"
    )


def test_assert_agent_evaluator_persona_in_shelves_shelves_load_and_degradation_matrix(
    tmp_path: Path,
) -> None:
    fnf_repo = tmp_path / "fnf"
    fnf_repo.mkdir()
    write_agent_evaluator_workflow_profile(fnf_repo, "fnf_wf", enabled=True, persona_id="some_id")
    with pytest.raises(FileNotFoundError):
        assert_agent_evaluator_persona_in_shelves(fnf_repo, "fnf_wf")

    ve_repo = tmp_path / "ve_scalar"
    ve_repo.mkdir()
    write_agent_evaluator_workflow_profile(ve_repo, "ve_wf", enabled=True, persona_id="some_id")
    write_persona_shelves(ve_repo, "scalar-not-a-mapping\n")
    with pytest.raises(ValueError, match=re.escape(_VE_LOAD_YAML_PREFIX)):
        assert_agent_evaluator_persona_in_shelves(ve_repo, "ve_wf")

    for case_id, shelves_body, expected_known in _DEGRADATION_CASES:
        case_repo = tmp_path / f"deg_{case_id}"
        case_repo.mkdir()
        write_agent_evaluator_workflow_profile(
            case_repo, "deg_wf", enabled=True, persona_id="not_in_shelves"
        )
        write_persona_shelves(case_repo, shelves_body)
        with pytest.raises(
            ValueError,
            match=re.escape(_VE_FRIENDLY_PREFIX),
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
    bare_repo = tmp_path / "bare"
    bare_repo.mkdir()

    # mypy: parse_agent_evaluator_workflow_block at line 25-26
    # explicitly handles None via str(workflow_profile).strip
    # short-circuit (early-return BEFORE workflow_profile_path).
    # The wrapper signature declares ``str`` but the parser
    # accepts ``str | None``; mypy ignore matches the runtime path.
    assert (
        assert_agent_evaluator_persona_in_shelves(bare_repo, None)  # type: ignore[arg-type]
        is None
    )
    assert assert_agent_evaluator_persona_in_shelves(bare_repo, "bad name") is None
    assert assert_agent_evaluator_persona_in_shelves(bare_repo, "does-not-exist") is None

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
