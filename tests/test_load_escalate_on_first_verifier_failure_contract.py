"""``load_escalate_on_first_verifier_failure`` direct contract.

The YAML reader at [verifier_escalation.py:10-24] is the workflow-profile-YAML
coercion-ladder twin of the fo62-fo74 env-layer matrix. Existing coverage is
one happy-path axis only
([tests/test_verifier_escalation_checkpoint.py] `test_load_escalate_on_first_
verifier_failure_default` exercises the shipped ``False`` default). The full
17-axis coercion-ladder is unpinned.

Behavioral asymmetry pinned in Part A: ``load_yaml`` from [merge.py:19-24]
raises ``ValueError`` if YAML root is not a mapping, so the helper
PROPAGATES ``ValueError`` for root-not-dict YAML rather than gracefully
returning ``False``. This diverges from other "graceful skip" loaders.

fo99 closes 4 unpinned surfaces via 4 parts spanning 17 axes
(~24 assertions, source unchanged):

* **Part A** -- structural type-guard ladder (4 axes -- file missing /
 root not dict (ValueError propagates) / verification key missing /
 verification not dict).
* **Part B** -- bool happy-path + missing-key fallback (3 axes -- bool True /
 bool False / target key missing under verification dict).
* **Part C** -- string truthy set + ``.strip().lower()`` normalization
 (5 axes -- literal "1"/"true"/"yes"/"on" / case-insensitive / whitespace-
 wrapped / combined case+whitespace / empty string lower-bound).
* **Part D** -- string falsy + non-bool/non-string type rejection (5 axes --
 literal "0"/"false"/"no"/"off" / arbitrary non-truthy strings / int 1+0 /
 float 1.0 / list+null).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_orchestrator.verifier_escalation import (
    load_escalate_on_first_verifier_failure,
)


def _write_policy(tmp_path: Path, body: str) -> Path:
    """Write ``configs/escalation/policy.yaml`` under tmp_path; return repo root."""
    policy_dir = tmp_path / "configs" / "escalation"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.yaml").write_text(body, encoding="utf-8")
    return tmp_path


def test_load_escalate_structural_type_guards_4_axis(tmp_path: Path) -> None:
    """Pin the 4 structural arms at verifier_escalation.py:13-18.

    A1 -- file missing -> File guard short-circuits to False.
    A2 -- root not a dict -> load_yaml raises ValueError; PROPAGATES (asymmetry).
    A3 -- verification key absent -> ver=None, isinstance(None, dict) False -> False.
    A4 -- verification scalar string -> isinstance non-dict False -> False.
    """
    bare_root = tmp_path / "a1_bare"
    bare_root.mkdir()
    assert load_escalate_on_first_verifier_failure(bare_root) is False, (
        "A1: configs/escalation/policy.yaml absent -> path.is_file() False -> return False"
    )

    a2_root = _write_policy(tmp_path / "a2_root", "- a\n- b\n- c\n")
    with pytest.raises(ValueError, match="YAML root must be a mapping"):
        load_escalate_on_first_verifier_failure(a2_root)

    a3_root = _write_policy(
        tmp_path / "a3_no_verification", "version: 1\nmax_retries_per_stage: 3\n",
    )
    assert load_escalate_on_first_verifier_failure(a3_root) is False, (
        "A3: verification key missing -> ver=None -> isinstance(None, dict) False -> False"
    )

    a4_root = _write_policy(
        tmp_path / "a4_verification_scalar", "verification: 'not a dict'\n",
    )
    assert load_escalate_on_first_verifier_failure(a4_root) is False, (
        "A4: verification is a string scalar -> isinstance(str, dict) False -> False"
    )


def test_load_escalate_bool_path_and_missing_key_3_axis(tmp_path: Path) -> None:
    """Pin bool literal pass-through + missing-key fallback at verifier_escalation.py:19-21.

    B1 -- bool True -> returns True (literal pass-through).
    B2 -- bool False -> returns False (literal pass-through, isolated from shipped default).
    B3 -- target key absent under verification dict -> v=None falls to fallback False.
    """
    b1_root = _write_policy(
        tmp_path / "b1_bool_true",
        "verification:\n  escalate_on_first_verifier_failure: true\n",
    )
    assert load_escalate_on_first_verifier_failure(b1_root) is True, (
        "B1: YAML bool true -> isinstance(v, bool) True -> return v -> True"
    )

    b2_root = _write_policy(
        tmp_path / "b2_bool_false",
        "verification:\n  escalate_on_first_verifier_failure: false\n",
    )
    assert load_escalate_on_first_verifier_failure(b2_root) is False, (
        "B2: YAML bool false -> isinstance(v, bool) True -> return v -> False (isolated "
        "from shipped repo default to pin contract in tmp_path)"
    )

    b3_root = _write_policy(
        tmp_path / "b3_target_key_absent",
        "verification:\n  auto_escalate_after_cumulative_findings: null\n",
    )
    assert load_escalate_on_first_verifier_failure(b3_root) is False, (
        "B3: verification dict present but target key absent -> v=None -> "
        "bool guard False, str guard False -> fallback return False"
    )


def test_load_escalate_string_truthy_set_5_axis(tmp_path: Path) -> None:
    """Pin string truthy set + .strip().lower() normalization at verifier_escalation.py:22-23.

    All YAML scalars MUST be explicitly quoted; PyYAML coerces unquoted
    ``true``/``yes``/``on`` to Python bool per YAML 1.1, which would hit the
    bool path instead of the string path.

    C1 -- literal truthy set: "1" / "true" / "yes" / "on" -> True.
    C2 -- case-insensitive: "TRUE" / "YES" / "On" / "True" -> True.
    C3 -- whitespace-wrapped: "  true  " / "\\tyes\\n" / "  on  " -> True.
    C4 -- combined: "  YES  " / "\\tTRUE\\n" -> True.
    C5 -- empty string "" -> False (lower bound; not in truthy set).
    """
    c1_dir = tmp_path / "c1"
    c1_dir.mkdir()
    for scalar in ("1", "true", "yes", "on"):
        root = _write_policy(
            c1_dir / scalar,
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is True, (
            f"C1 [{scalar!r}]: literal truthy string -> True (exact tuple match)"
        )

    c2_dir = tmp_path / "c2"
    c2_dir.mkdir()
    for i, scalar in enumerate(("TRUE", "YES", "On", "True")):
        root = _write_policy(
            c2_dir / f"case_{i}",
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is True, (
            f"C2 [{scalar!r}]: case-insensitive via .lower() -> True"
        )

    c3_dir = tmp_path / "c3"
    c3_dir.mkdir()
    c3_cases = [("c3_pad_true", "  true  "), ("c3_tab_yes", "\\tyes\\n"), ("c3_pad_on", "  on  ")]
    for case_name, scalar in c3_cases:
        root = _write_policy(
            c3_dir / case_name,
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is True, (
            f"C3 [{case_name}]: whitespace-wrapped via .strip() -> True"
        )

    c4_dir = tmp_path / "c4"
    c4_dir.mkdir()
    c4_cases = [("c4_pad_YES", "  YES  "), ("c4_tab_TRUE", "\\tTRUE\\n")]
    for case_name, scalar in c4_cases:
        root = _write_policy(
            c4_dir / case_name,
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is True, (
            f"C4 [{case_name}]: combined case + whitespace via .strip().lower() -> True"
        )

    c5_root = _write_policy(
        tmp_path / "c5_empty_string",
        'verification:\n  escalate_on_first_verifier_failure: ""\n',
    )
    assert load_escalate_on_first_verifier_failure(c5_root) is False, (
        "C5: empty string -> .strip().lower() is '' -> NOT in truthy set -> False (lower bound)"
    )


def test_load_escalate_string_falsy_and_type_reject_5_axis(tmp_path: Path) -> None:
    """Pin string falsy + non-bool/non-string type rejection at verifier_escalation.py:23-24.

    D1 -- literal falsy strings: "0" / "false" / "no" / "off" -> all False.
    D2 -- arbitrary non-truthy strings: "maybe" / "perhaps" / "truefoo" -> all False.
    D3 -- int 1 and 0 -> no numeric coercion (asymmetric vs env-layer).
    D4 -- float 1.0 -> reject.
    D5 -- list [] and null -> reject.
    """
    d1_dir = tmp_path / "d1"
    d1_dir.mkdir()
    for scalar in ("0", "false", "no", "off"):
        root = _write_policy(
            d1_dir / scalar,
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is False, (
            f"D1 [{scalar!r}]: literal falsy string NOT in truthy 4-tuple -> False; "
            "pins that the predicate is allowlist-style ('1','true','yes','on'), "
            "not denylist-style"
        )

    d2_dir = tmp_path / "d2"
    d2_dir.mkdir()
    for scalar in ("maybe", "perhaps", "truefoo"):
        root = _write_policy(
            d2_dir / scalar,
            f'verification:\n  escalate_on_first_verifier_failure: "{scalar}"\n',
        )
        assert load_escalate_on_first_verifier_failure(root) is False, (
            f"D2 [{scalar!r}]: arbitrary non-truthy string -> False; pins exact-match "
            "semantics (no prefix/substring -- 'truefoo' does not match 'true')"
        )

    d3_dir = tmp_path / "d3"
    d3_dir.mkdir()
    for n in (1, 0):
        root = _write_policy(
            d3_dir / f"int_{n}",
            f"verification:\n  escalate_on_first_verifier_failure: {n}\n",
        )
        assert load_escalate_on_first_verifier_failure(root) is False, (
            f"D3 [int {n}]: YAML int -> isinstance(v, bool) False (bool is subclass of int, "
            "but int is NOT subclass of bool) -> isinstance(v, str) False -> fallback False; "
            "asymmetric with env-layer _coerce_bool which often accepts string '1'"
        )

    d4_root = _write_policy(
        tmp_path / "d4_float",
        "verification:\n  escalate_on_first_verifier_failure: 1.0\n",
    )
    assert load_escalate_on_first_verifier_failure(d4_root) is False, (
        "D4: float 1.0 -> isinstance(v, bool) False -> isinstance(v, str) False -> False"
    )

    d5_root_list = _write_policy(
        tmp_path / "d5_list",
        "verification:\n  escalate_on_first_verifier_failure: []\n",
    )
    assert load_escalate_on_first_verifier_failure(d5_root_list) is False, (
        "D5 [list]: empty list -> isinstance False / False -> fallback False"
    )

    d5_root_null = _write_policy(
        tmp_path / "d5_null",
        "verification:\n  escalate_on_first_verifier_failure: null\n",
    )
    assert load_escalate_on_first_verifier_failure(d5_root_null) is False, (
        "D5 [null]: explicit null -> v=None -> isinstance False / False -> fallback False"
    )
