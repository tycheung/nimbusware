"""load_yaml`` root-type contract + sibling-parser cascade."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.workflow_escalation import (
    EscalationWorkflowBlock,
    parse_escalation_workflow_block,
)
from hermes_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)

_VALUE_ERROR_PREFIX = "YAML root must be a mapping: "


def _write_yaml(tmp_path: Path, body: str, name: str = "root.yaml") -> Path:
    """Write ``body`` to ``tmp_path/name`` and return the path."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _write_profile(tmp_path: Path, profile: str, body: str) -> None:
    """Write a workflow profile YAML under ``{tmp_path}/configs/workflows/``.

    Mirrors ``workflow_profile_path`` in
    [workflow_profiles.py](packages\\hermes_orchestrator\\workflow_profiles.py)
    expectations: file must exist at
    ``{repo_root}/configs/workflows/{profile}.yaml``.
    """
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{profile}.yaml").write_text(body, encoding="utf-8")


def test_load_yaml_dict_root_accept_arm_contract(tmp_path: Path) -> None:
    """Pin ``load_yaml`` dict-root accept arm: isinstance + inner preservation.

    Loops 10 dict-root variants spanning the YAML mapping surface that
    ``load_yaml`` should accept. Pins that **any mapping shape**
    (regardless of inner contents) is returned as a ``dict``.

    Pins 3 sub-contracts:

    1. **Dict-root passthrough** -- ``isinstance(result, dict)``.
    2. **Inner-content preservation** -- list / scalar (int / float /
       bool / str / null) / nested-mapping values survive intact.
    3. **Unicode round-trip** -- non-ASCII keys and values preserved.
    """
    cases: list[tuple[str, str, dict[str, object]]] = [
        ("empty_mapping", "{}", {}),
        ("single_key", "key: value", {"key": "value"}),
        ("multi_key_inline", "{a: 1, b: 2}", {"a": 1, "b": 2}),
        (
            "nested_mapping",
            "outer:\n  inner: value\n",
            {"outer": {"inner": "value"}},
        ),
        ("list_value", "items: [1, 2, 3]\n", {"items": [1, 2, 3]}),
        (
            "mixed_scalar_values",
            'n: 1\nf: 1.5\nb: true\ns: "hi"\nz: null\n',
            {"n": 1, "f": 1.5, "b": True, "s": "hi", "z": None},
        ),
        ("empty_list_value", "items: []\n", {"items": []}),
        ("empty_mapping_value", "nested: {}\n", {"nested": {}}),
        (
            "unicode_kv",
            '"\u043a\u043b\u044e\u0447": "\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435"\n',
            {"\u043a\u043b\u044e\u0447": "\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435"},
        ),
        (
            "block_multiline",
            "a: 1\nb: 2\nc: 3\nd: 4\n",
            {"a": 1, "b": 2, "c": 3, "d": 4},
        ),
    ]
    for i, (_name, body, expected) in enumerate(cases):
        path = _write_yaml(tmp_path, body, name=f"accept_{i}.yaml")
        result = load_yaml(path)
        assert isinstance(result, dict), (
            f"accept body={body!r}: result type {type(result).__name__} (should be dict)"
        )
        assert result == expected, f"accept body={body!r}: expected {expected}, got {result}"


def test_load_yaml_non_dict_root_value_error_contract(tmp_path: Path) -> None:
    """Pin ``load_yaml`` non-dict-root reject arm: ValueError + diagnostic.

    The core fo75 contract -- loop 11 non-dict-root variants and
    assert each raises ``ValueError`` with the operator-facing
    diagnostic. Pins both the **error type** AND the **error message**
    (the diagnostic is the path-disclosing string that surfaces in
    logs / ``RunOrchestrator.create_run`` exception paths).

    Pins 3 sub-contracts:

    1. **``ValueError``** -- not bare ``Exception`` / ``TypeError`` /
       custom subclass. Sibling parsers catch
       ``(OSError, ValueError, UnicodeDecodeError)`` so the exact
       exception class matters for the cascade to work.
    2. **Diagnostic prefix exactness** -- catches message-text
       refactors that drop ``"must be a mapping"`` or change
       capitalization.
    3. **Path inclusion in message** -- catches refactors that drop
       ``{path}`` interpolation (a real operator pain when a YAML
       config goes bad and the error doesn't say which file).
    """
    cases: list[tuple[str, str]] = [
        ("null_literal", "null\n"),
        ("empty_file", ""),
        ("whitespace_only", "   \n\n"),
        ("scalar_int", "42\n"),
        ("scalar_float", "3.14\n"),
        ("scalar_bool_true", "true\n"),
        ("scalar_bool_false", "false\n"),
        ("scalar_str_quoted", '"hello"\n'),
        ("sequence_empty", "[]\n"),
        ("sequence_non_empty", "[1, 2, 3]\n"),
        ("sequence_of_dicts", "- a: 1\n- b: 2\n"),
        ("tag_applied_scalar", "!!str 42\n"),
    ]
    for i, (_name, body) in enumerate(cases):
        path = _write_yaml(tmp_path, body, name=f"reject_{i}.yaml")
        with pytest.raises(ValueError) as exc_info:
            load_yaml(path)
        msg = str(exc_info.value)
        assert msg.startswith(_VALUE_ERROR_PREFIX), (
            f"reject body={body!r}: error message should start with "
            f"{_VALUE_ERROR_PREFIX!r}, got {msg!r}"
        )
        assert str(path) in msg, (
            f"reject body={body!r}: error message should include path {path!s}, got {msg!r}"
        )


def test_load_yaml_non_dict_root_cascades_to_sibling_parser_default_contract(
    tmp_path: Path,
) -> None:
    """Pin cascade-to-default for sibling parsers on non-dict YAML root.

    The **tie-in to the upcoming fo76 zero-behavior cleanup** -- pins
    that both ``parse_escalation_workflow_block`` in
    [workflow_escalation.py](packages\\hermes_orchestrator\\workflow_escalation.py)
    and ``parse_security_scan_metadata_on_verify_workflow`` in
    [workflow_security_metadata.py](packages\\hermes_orchestrator\\workflow_security_metadata.py)
    cascade to their respective defaults for every non-dict YAML root.

    The cascade chain:

    1. ``load_yaml`` raises ``ValueError`` (pinned in Part B).
    2. Parser's ``try/except (OSError, ValueError, UnicodeDecodeError)``
       catches.
    3. Parser returns the default (``EscalationWorkflowBlock()`` with
       ``suppress_automatic_escalation=False`` /
       ``parse_security_scan_metadata_on_verify_workflow`` returns
       ``False``).
    4. The outer ``if isinstance(raw, dict)`` guard at line 35 of
       [workflow_escalation.py](packages\\hermes_orchestrator\\workflow_escalation.py)
       and line 60 of
       [workflow_security_metadata.py](packages\\hermes_orchestrator\\workflow_security_metadata.py)
       **never executes** because the try/except returned first.

    Step 4 is the dead-code observation that justifies the fo76
    zero-behavior cleanup. The 5-block matrix below is the regression
    suite that proves behavior is preserved across the cleanup -- the
    same blocks must pass before AND after the guard removal.

    Block structure mirrors fo74 Part B's multi-path default
    convergence (5 blocks pinning that distinct inputs converge on the
    same default).
    """
    profile = "fo75_cascade"
    default_escalation = EscalationWorkflowBlock()
    blocks: list[tuple[str, str]] = [
        ("list_root", "- a: 1\n- b: 2\n"),
        ("scalar_int_root", "42\n"),
        ("scalar_str_root", '"hello"\n'),
        ("empty_root", ""),
        ("null_root", "null\n"),
    ]
    for block_id, body in blocks:
        _write_profile(tmp_path, profile, body)

        esc_result = parse_escalation_workflow_block(tmp_path, profile)
        assert esc_result == default_escalation, (
            f"{block_id} parser=parse_escalation_workflow_block: "
            f"expected default {default_escalation!r} via "
            f"load_yaml(ValueError) -> try/except cascade, got "
            f"{esc_result!r}"
        )
        assert esc_result.suppress_automatic_escalation is False, (
            f"{block_id} parser=parse_escalation_workflow_block: "
            f"suppress_automatic_escalation should be False (default), "
            f"got {esc_result.suppress_automatic_escalation!r}"
        )

        sec_result = parse_security_scan_metadata_on_verify_workflow(
            tmp_path,
            profile,
        )
        assert sec_result is False, (
            f"{block_id} parser=parse_security_scan_metadata_on_verify_workflow: "
            f"expected False (default) via load_yaml(ValueError) -> "
            f"try/except cascade, got {sec_result!r}"
        )
