"""yaml.YAMLError`` propagation divergence at ``load_yaml``."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.workflow_escalation import (
    parse_escalation_workflow_block,
)
from nimbusware_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)

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


def _write_yaml(tmp_path: Path, body: str, name: str = "root.yaml") -> Path:
    """Write ``body`` to ``tmp_path/name`` and return the path."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _write_profile(tmp_path: Path, profile: str, body: str) -> None:
    """Write a workflow profile YAML under ``{tmp_path}/configs/workflows/``.

    Mirrors ``workflow_profile_path`` in
    [workflow_profiles.py](packages\\nimbusware_orchestrator\\workflow_profiles.py)
    expectations: file must exist at
    ``{repo_root}/configs/workflows/{profile}.yaml``.
    """
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{profile}.yaml").write_text(body, encoding="utf-8")


def test_load_yaml_malformed_yaml_propagates_yaml_error_contract(
    tmp_path: Path,
) -> None:
    """Pin ``load_yaml`` malformed-YAML reject: raises ``yaml.YAMLError``.

    Loops 8 malformed YAML variants spanning the three PyYAML error
    classes that ``safe_load`` raises: ``ScannerError`` (lexical, most
    common), ``ParserError`` (syntactic), and ``ComposerError``
    (alias / anchor resolution).

    Pins 2 sub-contracts per case:

    1. **``yaml.YAMLError``** -- the umbrella class for every PyYAML
       parsing error. Asserted via ``pytest.raises(yaml.YAMLError)``;
       a future refactor that wraps the exception in a custom class
       (e.g. ``NimbuswareYamlError``) would fail with "DID NOT RAISE"
       unless that class extends ``yaml.YAMLError``.
    2. **Non-membership in the cascade-catchable tuple** --
       ``not isinstance(exc, (OSError, ValueError, UnicodeDecodeError))``.
       This is what causes the sibling-parser cascade in fo75 Part C
       to NOT catch malformed YAML; Part B documents the same fact at
       the type-system level. Asserting it per-case here means any
       hypothetical refactor that subclasses (e.g.) ``ValueError`` for
       a custom YAML error would surface as a test failure pointing
       at the specific malformed body.
    """
    for i, (case_id, body) in enumerate(_MALFORMED_BODIES):
        path = _write_yaml(tmp_path, body, name=f"malformed_{i}.yaml")
        with pytest.raises(yaml.YAMLError) as exc_info:
            load_yaml(path)
        exc = exc_info.value
        assert isinstance(exc, yaml.YAMLError), (
            f"malformed {case_id}: expected yaml.YAMLError, got {type(exc).__name__}"
        )
        assert not isinstance(
            exc,
            (OSError, ValueError, UnicodeDecodeError),
        ), (
            f"malformed {case_id}: {type(exc).__name__} should NOT "
            f"subclass the sibling-parser cascade-catchable tuple "
            f"(OSError, ValueError, UnicodeDecodeError); if it does, "
            f"fo75/fo76 Part C contracts diverge silently"
        )


def test_load_yaml_yaml_error_class_hierarchy_contract() -> None:
    """Pin ``yaml.YAMLError`` class hierarchy boundary.

    The single-test class-hierarchy contract (no per-case loop, no
    I/O -- these are static facts about the imported ``yaml`` module).
    Pins the **boundary condition** that justifies the cascade
    divergence at the type-system level.

    A refactor of PyYAML (or a re-aliasing inside this codebase) that
    makes ``yaml.YAMLError`` a ``ValueError`` would flip the sibling
    parsers' cascade from propagate-to-caller to cascade-to-default
    for malformed YAML -- a real behavioral change that Part B
    documents at the type-system level so the regression surfaces
    BEFORE any test fixture is even loaded.
    """
    assert issubclass(yaml.YAMLError, Exception), (
        "yaml.YAMLError should be a regular Exception subclass "
        f"(MRO: {[c.__name__ for c in yaml.YAMLError.__mro__]})"
    )
    assert not issubclass(yaml.YAMLError, ValueError), (
        "yaml.YAMLError MUST NOT subclass ValueError -- if it does, "
        "the sibling-parser try/except (OSError, ValueError, "
        "UnicodeDecodeError) would silently cascade malformed YAML "
        "to default and fo76 Part C would start failing with 'DID "
        "NOT RAISE'"
    )
    assert not issubclass(yaml.YAMLError, OSError), (
        "yaml.YAMLError MUST NOT subclass OSError -- file-error tuple "
        "member, same cascade-flip concern"
    )
    assert not issubclass(yaml.YAMLError, UnicodeDecodeError), (
        "yaml.YAMLError MUST NOT subclass UnicodeDecodeError -- "
        "decode-error tuple member, same cascade-flip concern"
    )
    expected_mro_head = (yaml.YAMLError, Exception, BaseException, object)
    actual_mro_head = yaml.YAMLError.__mro__[:4]
    assert actual_mro_head == expected_mro_head, (
        f"yaml.YAMLError.__mro__[:4] should be {expected_mro_head!r} "
        f"so any PyYAML upgrade that injects a new base class "
        f"surfaces here as a deliberate cascade-enabling change "
        f"rather than a silent behavioral flip; got {actual_mro_head!r}"
    )


def test_load_yaml_malformed_yaml_propagates_through_sibling_parsers_contract(
    tmp_path: Path,
) -> None:
    """Pin malformed-YAML propagation through sibling parsers.

    The **structural inversion of fo75 Part C** -- pins that for
    malformed YAML, both sibling parsers PROPAGATE ``yaml.YAMLError``
    rather than cascading to default.

    Loop 8 ``_MALFORMED_BODIES`` x 2 parsers (16 cases). Per case:
    write the malformed body to a workflow profile, call each parser,
    assert ``pytest.raises(yaml.YAMLError)``.

    The cascade chain (or rather, the **absent** cascade):

    1. ``load_yaml`` propagates ``yaml.YAMLError`` from
       ``yaml.safe_load`` (pinned in Part A).
    2. Parser's ``try/except (OSError, ValueError, UnicodeDecodeError)``
       does NOT catch ``yaml.YAMLError`` because of the class-hierarchy
       boundary (pinned in Part B).
    3. ``yaml.YAMLError`` propagates out of the parser to the caller.

    A future cascade-enabling refactor (adding ``yaml.YAMLError`` to
    the parsers' except tuple) would flip ``pytest.raises`` to
    ``DID NOT RAISE`` -- Part C fails loudly on exactly that change,
    and the refactor PR would update Part C to assert
    cascade-to-default (mirroring fo75 Part C).
    """
    profile = "fo76_propagate"
    for case_id, body in _MALFORMED_BODIES:
        _write_profile(tmp_path, profile, body)

        with pytest.raises(yaml.YAMLError) as esc_exc_info:
            parse_escalation_workflow_block(tmp_path, profile)
        assert isinstance(esc_exc_info.value, yaml.YAMLError), (
            f"{case_id} parser=parse_escalation_workflow_block: "
            f"expected yaml.YAMLError to propagate, got "
            f"{type(esc_exc_info.value).__name__}"
        )

        with pytest.raises(yaml.YAMLError) as sec_exc_info:
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                profile,
            )
        assert isinstance(sec_exc_info.value, yaml.YAMLError), (
            f"{case_id} parser=parse_security_scan_metadata_on_verify_workflow: "
            f"expected yaml.YAMLError to propagate, got "
            f"{type(sec_exc_info.value).__name__}"
        )
