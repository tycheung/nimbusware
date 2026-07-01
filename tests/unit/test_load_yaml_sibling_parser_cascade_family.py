from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from nimbusware_orchestrator.integrator_gate import _integrator_gate_workflow_dict
from nimbusware_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorWorkflowBlock,
    parse_agent_evaluator_workflow_block,
)
from nimbusware_orchestrator.workflow_blocks_simple import (
    EscalationWorkflowBlock,
    parse_escalation_workflow_block,
)
from nimbusware_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)
from nimbusware_orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
)
from nimbusware_orchestrator.workflow_universal_critique import (
    UniversalCritiqueWorkflowBlock,
    parse_universal_critique_workflow_block,
)
from unit.composite_repo_fixtures import write_workflow_profile

_NON_DICT_ROOT_BLOCKS: list[tuple[str, str]] = [
    ("list_root", "- a: 1\n- b: 2\n"),
    ("scalar_int_root", "42\n"),
    ("scalar_str_root", '"hello"\n'),
    ("empty_root", ""),
    ("null_root", "null\n"),
]


_MALFORMED_BODIES: list[tuple[str, str]] = [
    ("unterminated_flow_map", "{"),
    ("unterminated_flow_seq", "["),
    ("unterminated_with_content_map", "{foo: bar"),
    ("unterminated_with_content_seq", "[1, 2"),
    ("tab_indent", "foo:\n\tbar: baz"),
    ("unclosed_double_quote", '"unclosed'),
    ("unclosed_single_quote", "'unclosed"),
    ("undefined_anchor", "*undefined_anchor"),
]


_ParserCallable = Callable[[Path, str | None], Any]


_FAMILY_PARSERS: list[tuple[str, _ParserCallable, object]] = [
    (
        "parse_agent_evaluator_workflow_block",
        parse_agent_evaluator_workflow_block,
        AgentEvaluatorWorkflowBlock(),
    ),
    (
        "parse_self_refinement_workflow_block",
        parse_self_refinement_workflow_block,
        SelfRefinementWorkflowBlock(),
    ),
    (
        "parse_universal_critique_workflow_block",
        parse_universal_critique_workflow_block,
        UniversalCritiqueWorkflowBlock(),
    ),
    (
        "_integrator_gate_workflow_dict",
        _integrator_gate_workflow_dict,
        None,
    ),
]


_ALL_FAMILY_PARSERS: list[tuple[str, _ParserCallable, object]] = [
    *_FAMILY_PARSERS,
    (
        "parse_escalation_workflow_block",
        parse_escalation_workflow_block,
        EscalationWorkflowBlock(),
    ),
    (
        "parse_security_scan_metadata_on_verify_workflow",
        parse_security_scan_metadata_on_verify_workflow,
        False,
    ),
]


def test_non_dict_root_cascades_to_default_across_sibling_parser_family_contract(
    tmp_path: Path,
) -> None:
    """Pin non-dict YAML root cascade-to-default across the 4 new family parsers.

    Mirrors fo75 Part C structure -- loops 5 non-dict root blocks
    (list / scalar int / scalar str / empty file / null literal) x 4
    sibling parsers (agent_evaluator, self_refinement,
    universal_critique, integrator_gate) = **20 cases**.

    Per case the cascade chain is:

    1. ``load_yaml`` raises ``ValueError`` for non-dict YAML root
       (fo75 Part B pinned the loader-level reject).
    2. Parser's ``try/except (OSError, ValueError, UnicodeDecodeError)``
       catches.
    3. Parser returns its specific default
       (``AgentEvaluatorWorkflowBlock()`` /
       ``SelfRefinementWorkflowBlock()`` /
       ``UniversalCritiqueWorkflowBlock()`` (all-False) / ``None`` for
       ``_integrator_gate_workflow_dict``).
    4. Any post-`load_yaml` ``isinstance(raw, dict)`` guard (present
       in ``workflow_universal_critique.py`` and
       ``integrator_gate.py``) **never executes** because the
       try/except returned first -- the dead-code observation that
       fo78 zero-behavior cleanup will remove.

    The matrix is the regression suite that guarantees behavior is
    preserved across the fo78 cleanup AND across any future cascade-
    harden refactor (which would update Part B but leave Part A
    intact -- non-dict roots still cascade via ``ValueError``).
    """
    profile = "fo77_cascade"
    for block_id, body in _NON_DICT_ROOT_BLOCKS:
        write_workflow_profile(tmp_path, profile, body)
        for parser_name, parser_callable, expected_default in _FAMILY_PARSERS:
            result = parser_callable(tmp_path, profile)
            assert result == expected_default, (
                f"{block_id} parser={parser_name}: expected default "
                f"{expected_default!r} via load_yaml(ValueError) -> "
                f"try/except cascade, got {result!r}"
            )


def test_malformed_yaml_propagates_through_sibling_parser_family_contract(
    tmp_path: Path,
) -> None:
    """Pin malformed-YAML propagation across the 4 new family parsers.

    The **structural inversion of Part A** -- mirrors fo76 Part C
    structure across the 4 new sibling parsers. Loops 8 malformed
    bodies spanning ``ScannerError`` / ``ComposerError`` x 4 parsers
    = **32 cases**.

    The cascade chain is **absent** because:

    1. ``load_yaml`` propagates ``yaml.YAMLError`` from
       ``yaml.safe_load`` (fo76 Part A pinned the loader-level
       propagation).
    2. Parser's ``try/except (OSError, ValueError, UnicodeDecodeError)``
       does NOT catch ``yaml.YAMLError`` (fo76 Part B class-hierarchy
       boundary).
    3. ``yaml.YAMLError`` propagates out of the parser to the caller.

    A future fo78 cascade-harden refactor (adding ``yaml.YAMLError``
    to all 6 parsers' except tuples in lockstep) would flip these
    ``pytest.raises`` to cascade-to-default; the refactor PR would
    update Part B to mirror Part A's assertion shape, making the
    test diff the intentional behavioral change record.
    """
    profile = "fo77_propagate"
    for case_id, body in _MALFORMED_BODIES:
        write_workflow_profile(tmp_path, profile, body)
        for parser_name, parser_callable, _expected_default in _FAMILY_PARSERS:
            with pytest.raises(yaml.YAMLError) as exc_info:
                parser_callable(tmp_path, profile)
            assert isinstance(exc_info.value, yaml.YAMLError), (
                f"{case_id} parser={parser_name}: expected "
                f"yaml.YAMLError to propagate, got "
                f"{type(exc_info.value).__name__}"
            )


def test_sibling_parser_family_cascade_tuple_uniformity_contract(
    tmp_path: Path,
) -> None:
    """Pin cross-parser uniformity across all 6 family parsers.

    The **cross-parser uniformity meta-contract** -- pins that all 6
    family parsers (2 fo75/fo76 + 4 new) handle a single
    ``ValueError``-producing root AND a single
    ``yaml.YAMLError``-producing body identically. 12 assertions
    total (6 parsers x 2 axes).

    Pins the **divergence-resistance contract**: if any single parser
    drifts its except tuple (e.g., adds ``yaml.YAMLError`` to the
    catch-list while the others retain
    ``(OSError, ValueError, UnicodeDecodeError)``), the test diff
    shows exactly which parser broke uniformity AND which axis
    diverged.

    This is also the regression-suite scaffolding for the optional
    fo78 cascade-harden refactor -- the refactor flips the
    ``yaml.YAMLError`` axis from ``pytest.raises`` to cascade-to-
    default across all 6 in lockstep, producing a parallel test diff
    rather than a one-parser-at-a-time drift.

    Canonical bodies:

    * ``"null\\n"`` -- minimal ``ValueError``-producing root (fo75
      Part B case ``null_literal``); ``load_yaml`` raises
      ``ValueError`` with the ``"YAML root must be a mapping"``
      diagnostic.
    * ``"{"`` -- minimal ``yaml.YAMLError``-producing body (fo76
      Part A case ``unterminated_flow_map``); ``yaml.safe_load``
      raises ``ScannerError``.
    """
    canonical_value_error_body = "null\n"
    canonical_yaml_error_body = "{"

    for parser_name, parser_callable, expected_default in _ALL_FAMILY_PARSERS:
        write_workflow_profile(tmp_path, "fo77_uniform_ve", canonical_value_error_body)
        result = parser_callable(tmp_path, "fo77_uniform_ve")
        assert result == expected_default, (
            f"uniformity parser={parser_name}: ValueError cascade "
            f"should converge on default {expected_default!r}, got "
            f"{result!r}"
        )

        write_workflow_profile(tmp_path, "fo77_uniform_ye", canonical_yaml_error_body)
        with pytest.raises(yaml.YAMLError) as exc_info:
            parser_callable(tmp_path, "fo77_uniform_ye")
        assert isinstance(exc_info.value, yaml.YAMLError), (
            f"uniformity parser={parser_name}: yaml.YAMLError should "
            f"propagate, got {type(exc_info.value).__name__}"
        )
