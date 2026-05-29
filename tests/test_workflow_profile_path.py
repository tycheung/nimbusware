"""``workflow_profile_path`` 3-axis contract + cross-caller divergence.

[`workflow_profile_path`](d:\\Hermes\\packages\\hermes_orchestrator\\workflow_profiles.py)
is the orchestrator's **profile-name-to-file-path gatekeeper**, called
BEFORE `load_yaml` by every sibling cascade parser:

```python
def workflow_profile_path(repo_root: Path, profile: str) -> Path:
 key = profile.strip()
 if not key or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", key):
 msg = f"invalid workflow_profile: {profile!r}"
 raise ValueError(msg)
 path = repo_root / "configs" / "workflows" / f"{key}.yaml"
 if not path.is_file():
 msg = f"unknown workflow_profile (no file): {profile!r}"
 raise FileNotFoundError(msg)
 return path
```

Three-axis contract:

1. **Accept arm** -- ``.strip()``-normalized name passing
 ``[a-zA-Z0-9][a-zA-Z0-9_.-]*`` regex AND existing file -> return
 ``Path``.
2. **ValueError reject arm** -- empty after strip OR regex-invalid ->
 ``ValueError("invalid workflow_profile: {profile!r}")``.
3. **FileNotFoundError reject arm** -- regex-valid name BUT resolved
 path is not a file ->
 ``FileNotFoundError("unknown workflow_profile (no file): {profile!r}")``.

Zero existing direct unit tests; the diagnostic strings appear only at
[workflow_profiles.py:13](d:\\Hermes\\packages\\hermes_orchestrator\\workflow_profiles.py)
and line 17 with no test asserting them. fo79 is the path-resolution
analog of the fo75.

Two caller classes at the path-resolution layer feed Part C's
divergence contract:

* **Cascading callers (6 sibling parsers)** wrap
 ``workflow_profile_path`` in
 ``try/except (FileNotFoundError, OSError, ValueError)`` -> return
 their respective default.
* **Propagating callers** call ``workflow_profile_path`` without
 try/except -> propagate. ``load_scraper_fetch_config`` at
 [scraper_stage.py:28-29](d:\\Hermes\\packages\\hermes_orchestrator\\scraper_stage.py)
 is the clean representative used in Part C (ingress /
 RunOrchestrator.create_run also propagate but require complex
 registry / orchestrator fixtures).

Three parts:

* **Part A** locks the accept arm -- 8 accept variants pinning Path
 return type, exact path, ``is_file()`` post-condition, directory
 plumbing, ``.yaml`` suffix, and ``.strip()`` normalization rescue.
* **Part B** locks the two reject arms -- 14 ``_INVALID_NAMES``
 (ValueError) + 5 ``_MISSING_VARIANTS`` (FileNotFoundError) asserting
 exception class + diagnostic prefix + ``{profile!r}`` repr inclusion;
 pins the **reject-order** (regex BEFORE file existence).
* **Part C** locks the cascade-vs-propagate divergence -- 6 sibling
 parsers (cascade to default for both axes, 12 assertions) +
 ``load_scraper_fetch_config`` (propagates both axes, 2 assertions),
 14 total assertions. Pins that the cascade-tuple uniformity at this
 layer mirrors the ``load_yaml``-layer uniformity from fo77 Part C
 AND that the propagating-caller class is structurally distinct.

Cross-slice symmetry:

| Slice | Boundary | Accept | Reject | Cascade/propagate |
|-------|----------|--------|--------|-------------------|
| fo75 | load_yaml root type | A | B (VE) | C (6 cascade) |
| fo76 | load_yaml malformed | (n/a) | A+B (YAMLError + MRO) | C (6 propagate) |
| fo77 | load_yaml cascade family | (n/a) | (n/a) | A/B/C (4 new + uniformity) |
| **fo79** | **wpp** | **A** | **B (VE + FNF)** | **C (6 cascade + 1 propagate)** |
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from hermes_orchestrator.integrator_gate import _integrator_gate_workflow_dict
from hermes_orchestrator.scraper_stage import load_scraper_fetch_config
from hermes_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorWorkflowBlock,
    parse_agent_evaluator_workflow_block,
)
from hermes_orchestrator.workflow_escalation import (
    EscalationWorkflowBlock,
    parse_escalation_workflow_block,
)
from hermes_orchestrator.workflow_profiles import workflow_profile_path
from hermes_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)
from hermes_orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
)
from hermes_orchestrator.workflow_universal_critique import (
    UniversalCritiqueWorkflowBlock,
    parse_universal_critique_workflow_block,
)

_VALUE_ERROR_PREFIX = "invalid workflow_profile: "
_FILE_NOT_FOUND_PREFIX = "unknown workflow_profile (no file): "


_INVALID_NAMES: list[tuple[str, str]] = [
    ("empty_string", ""),
    ("whitespace_only_spaces", "   "),
    ("whitespace_only_tabs", "\t\t"),
    ("starts_with_underscore", "_foo"),
    ("starts_with_dot", ".foo"),
    ("starts_with_dash", "-foo"),
    ("contains_space", "foo bar"),
    ("contains_forward_slash", "foo/bar"),
    ("contains_backslash", "foo\\bar"),
    ("contains_asterisk", "foo*"),
    ("contains_colon", "foo:bar"),
    ("non_ascii_unicode", "caf\u00e9"),
    ("path_traversal_dotdot", ".."),
    ("path_traversal_relative", "../foo"),
]


_MISSING_VARIANTS: list[tuple[str, str]] = [
    ("file_does_not_exist", "no_such_profile"),
    ("dir_exists_file_absent", "absent_in_existing_dir"),
    ("name_collides_with_subdir", "is_a_directory"),
    ("name_with_dots", "no.such.profile"),
    ("name_with_dashes_underscores", "no-such_profile"),
]


_ParserCallable = Callable[[Path, "str | None"], Any]


_ALL_FAMILY_PARSERS: list[tuple[str, _ParserCallable, object]] = [
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


def _make_workflows_dir(tmp_path: Path) -> Path:
    """Ensure ``{tmp_path}/configs/workflows/`` exists and return it."""
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    return wf_dir


def _write_profile(
    tmp_path: Path, name: str, body: str = "version: 1\n",
) -> Path:
    """Write a minimal valid profile file under ``configs/workflows``.

    Returns the path written. The default body is a valid mapping root
    so any caller of ``load_yaml`` on this file succeeds.
    """
    wf_dir = _make_workflows_dir(tmp_path)
    path = wf_dir / f"{name}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_workflow_profile_path_accept_arm_normalizes_and_returns_path_contract(
    tmp_path: Path,
) -> None:
    """Pin ``workflow_profile_path`` accept arm: Path + normalization.

    Loops 8 accept-arm variants spanning the regex surface that
    ``workflow_profile_path`` should accept. Pins that **any
    regex-valid name** with an existing file resolves to the expected
    Path with the correct directory plumbing and ``.yaml`` suffix.

    Pins 5 sub-contracts per case:

    1. **Path return type** -- ``isinstance(result, Path)``.
    2. **Exact path match** -- equality against constructed expected.
    3. **File post-condition** -- ``result.is_file()`` (the function
       checked this before returning).
    4. **Directory plumbing** -- ``result.parent.name == "workflows"``
       AND ``result.parent.parent.name == "configs"`` (catches
       refactors that move the directory layout).
    5. **``.yaml`` suffix** -- catches refactors that change the
       extension or stop appending it.

    The ``strip_rescue_whitespace`` case additionally pins the
    ``.strip()`` normalization: input ``"  foo  "`` resolves to
    ``foo.yaml`` (NOT ``"  foo  ".yaml`` or
    ``"  foo  .yaml"``).
    """
    cases: list[tuple[str, str, str]] = [
        ("canonical", "foo", "foo"),
        ("dots_in_name", "foo.bar", "foo.bar"),
        ("dashes_in_name", "foo-bar", "foo-bar"),
        ("underscores_in_name", "foo_bar", "foo_bar"),
        ("uppercase_name", "FOO", "FOO"),
        ("mixed_alphanumeric", "FooBar123", "FooBar123"),
        ("all_digits", "123", "123"),
        ("strip_rescue_whitespace", "  foo_strip  ", "foo_strip"),
    ]
    for case_id, profile_input, stripped_name in cases:
        expected = _write_profile(tmp_path, stripped_name)
        result = workflow_profile_path(tmp_path, profile_input)
        assert isinstance(result, Path), (
            f"accept {case_id} input={profile_input!r}: result type "
            f"{type(result).__name__} (should be Path)"
        )
        assert result == expected, (
            f"accept {case_id} input={profile_input!r}: expected "
            f"{expected!s}, got {result!s}"
        )
        assert result.is_file(), (
            f"accept {case_id} input={profile_input!r}: result path "
            f"{result!s} should be a file (post-condition of the "
            f"is_file() check inside workflow_profile_path)"
        )
        assert result.parent.name == "workflows", (
            f"accept {case_id} input={profile_input!r}: "
            f"result.parent.name should be 'workflows', got "
            f"{result.parent.name!r}"
        )
        assert result.parent.parent.name == "configs", (
            f"accept {case_id} input={profile_input!r}: "
            f"result.parent.parent.name should be 'configs', got "
            f"{result.parent.parent.name!r}"
        )
        assert result.suffix == ".yaml", (
            f"accept {case_id} input={profile_input!r}: result.suffix "
            f"should be '.yaml', got {result.suffix!r}"
        )


def test_workflow_profile_path_reject_arms_value_error_and_file_not_found_contract(
    tmp_path: Path,
) -> None:
    """Pin ``workflow_profile_path`` reject arms: ValueError + FNF.

    The core fo79 contract -- two reject sub-arms in one test
    (parallels fo75 Part B's reject-loop pattern).

    **Sub-arm 1 (ValueError axis):** 14 ``_INVALID_NAMES`` variants
    spanning the regex-reject surface (empty / whitespace-only /
    non-alphanumeric start / forbidden body chars / non-ASCII / path
    traversal). Each asserts:

    1. **``ValueError``** -- not bare ``Exception`` or
       ``FileNotFoundError``; the exact class matters because the 6
       cascading callers' ``except (FileNotFoundError, OSError,
       ValueError)`` tuple depends on it (fo77 Part C
       uniformity).
    2. **Diagnostic prefix exactness** -- ``"invalid
       workflow_profile: "``; catches refactors that drop the
       diagnostic.
    3. **``{profile!r}`` repr inclusion** -- pins that the ORIGINAL
       (unstripped, unsanitized) name appears in the message via
       ``repr()``; catches refactors that drop the value, use
       ``{profile}`` non-repr (loses quoting / escaping for empty
       strings / whitespace), or substitute the stripped key.

    **Sub-arm 2 (FileNotFoundError axis):** 5 ``_MISSING_VARIANTS``
    variants pinning that a regex-VALID name resolves to a missing
    file -> FileNotFoundError. Pins the **reject-order**: regex
    check happens BEFORE file existence check (any case in sub-arm 1
    would raise ValueError even if the file existed; sub-arm 2 cases
    raise FileNotFoundError only after passing the regex). The
    ``name_collides_with_subdir`` case pins that ``is_file()``
    returns False for directories, not just for non-existent paths.
    """
    for case_id, invalid_name in _INVALID_NAMES:
        with pytest.raises(ValueError) as exc_info:
            workflow_profile_path(tmp_path, invalid_name)
        msg = str(exc_info.value)
        assert msg.startswith(_VALUE_ERROR_PREFIX), (
            f"value_error {case_id} input={invalid_name!r}: error "
            f"message should start with {_VALUE_ERROR_PREFIX!r}, got "
            f"{msg!r}"
        )
        assert repr(invalid_name) in msg, (
            f"value_error {case_id} input={invalid_name!r}: error "
            f"message should include the original {{profile!r}} value "
            f"{repr(invalid_name)!r}, got {msg!r}"
        )

    _make_workflows_dir(tmp_path)
    (tmp_path / "configs" / "workflows" / "is_a_directory.yaml").mkdir()
    for case_id, missing_name in _MISSING_VARIANTS:
        with pytest.raises(FileNotFoundError) as exc_info:
            workflow_profile_path(tmp_path, missing_name)
        msg = str(exc_info.value)
        assert msg.startswith(_FILE_NOT_FOUND_PREFIX), (
            f"file_not_found {case_id} input={missing_name!r}: error "
            f"message should start with {_FILE_NOT_FOUND_PREFIX!r}, "
            f"got {msg!r}"
        )
        assert repr(missing_name) in msg, (
            f"file_not_found {case_id} input={missing_name!r}: error "
            f"message should include the original {{profile!r}} value "
            f"{repr(missing_name)!r}, got {msg!r}"
        )


def test_workflow_profile_path_cascade_vs_propagate_divergence_at_path_resolution_layer_contract(
    tmp_path: Path,
) -> None:
    """Pin cross-caller divergence at the path-resolution layer.

    The cross-caller divergence meta-contract -- pins the two
    distinct behavior classes at the path-resolution layer:

    1. **Cascading callers (6 sibling parsers)** UNIFORMLY catch both
       ``ValueError`` (from regex-invalid name) and
       ``FileNotFoundError`` (from missing file) and cascade to their
       respective defaults. Mirrors fo77 Part C uniformity at the
       ``load_yaml`` layer.
    2. **Propagating caller (``load_scraper_fetch_config``)**
       UNIFORMLY propagates both exception classes (no try/except
       around ``workflow_profile_path``). Structural inversion of the
       cascade sub-loop.

    The divergence is **deliberate** -- cascade for "workflow
    override" semantics where missing/invalid means "use defaults",
    propagate for "scraper config" semantics where missing/invalid is
    a hard error.

    A future refactor that adds try/except to
    ``load_scraper_fetch_config`` would flip sub-loop 2 from
    ``pytest.raises`` to cascade-to-default -- the test diff
    documents the intentional behavioral change (mirroring the
    fo76 -> cascade-harden pattern).

    Canonical inputs:

    * ``"foo bar"`` -- regex-invalid (contains space), strips to
      ``"foo bar"`` (non-empty), reaches workflow_profile_path which
      raises ``ValueError``.
    * ``"no_such_profile"`` -- regex-valid (matches fullmatch), file
      doesn't exist under ``{tmp_path}/configs/workflows/``,
      workflow_profile_path raises ``FileNotFoundError``.
    """
    canonical_invalid_name = "foo bar"
    canonical_missing_file = "no_such_profile"

    for parser_name, parser_callable, expected_default in _ALL_FAMILY_PARSERS:
        ve_result = parser_callable(tmp_path, canonical_invalid_name)
        assert ve_result == expected_default, (
            f"cascade value_error parser={parser_name}: "
            f"invalid-name {canonical_invalid_name!r} should cascade "
            f"to default {expected_default!r} via "
            f"workflow_profile_path(ValueError) -> try/except, got "
            f"{ve_result!r}"
        )
        fnf_result = parser_callable(tmp_path, canonical_missing_file)
        assert fnf_result == expected_default, (
            f"cascade file_not_found parser={parser_name}: missing "
            f"file {canonical_missing_file!r} should cascade to "
            f"default {expected_default!r} via "
            f"workflow_profile_path(FileNotFoundError) -> "
            f"try/except, got {fnf_result!r}"
        )

    with pytest.raises(ValueError) as ve_exc_info:
        load_scraper_fetch_config(tmp_path, canonical_invalid_name)
    assert isinstance(ve_exc_info.value, ValueError), (
        f"propagate value_error caller=load_scraper_fetch_config: "
        f"invalid-name {canonical_invalid_name!r} should propagate "
        f"ValueError (no try/except around workflow_profile_path), "
        f"got {type(ve_exc_info.value).__name__}"
    )

    with pytest.raises(FileNotFoundError) as fnf_exc_info:
        load_scraper_fetch_config(tmp_path, canonical_missing_file)
    assert isinstance(fnf_exc_info.value, FileNotFoundError), (
        f"propagate file_not_found caller=load_scraper_fetch_config: "
        f"missing file {canonical_missing_file!r} should propagate "
        f"FileNotFoundError (no try/except around "
        f"workflow_profile_path), got "
        f"{type(fnf_exc_info.value).__name__}"
    )
