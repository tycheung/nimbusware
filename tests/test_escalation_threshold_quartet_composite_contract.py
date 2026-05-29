"""``configs/escalation/policy.yaml`` quartet loader composite.

Four sibling pure helpers in
[escalation_threshold.py:10-66](packages/hermes_orchestrator/escalation_threshold.py)
read the **same** ``configs/escalation/policy.yaml`` file independently
and form the lower layer beneath the cumulative-escalation emitter
quartet and ``_maybe_emit_anti_deadlock_escalation``.
All four share an IDENTICAL 4-arm defensive shape but each consumes a
DIFFERENT verification-subkey:

```python
def loader(repo_root: Path) -> int | None:
 path = repo_root / "configs" / "escalation" / "policy.yaml"
 if not path.is_file():
 return None
 raw = load_yaml(path)
 ver = raw.get("verification")
 if not isinstance(ver, dict):
 return None
 n = ver.get(KEY)
 if isinstance(n, int) and n >= 1:
 return n
 return None
```

| Loader | Verification subkey |
|--------------------------------------------------|--------------------------------------------|
| ``load_auto_escalate_after_cumulative_findings`` | ``auto_escalate_after_cumulative_findings`` |
| ``load_notice_escalate_at_cumulative_findings`` | ``notice_escalate_at_cumulative_findings`` |
| ``load_escalate_after_cumulative_stage_failures``| ``escalate_after_cumulative_stage_failures``|
| ``load_escalate_after_cumulative_gate_failures`` | ``escalate_after_cumulative_gate_failures`` |

Existing coverage is sampled only:

* [tests/test_escalation_threshold.py](tests/test_escalation_threshold.py)
 -- 4 tests: ROOT-no-key fallback for 3 of 4 loaders, plus one happy
 integer sample for each of 3 loaders. ``load_notice_escalate_at_cumulative_findings``
 has NO direct test (only ``patch``ed in
 [tests/test_cumulative_escalation_emitter_quartet_contract.py](tests/test_cumulative_escalation_emitter_quartet_contract.py)).

No direct tests for: file-absent fallback, ``verification`` non-dict
arm, non-int value arm, boundary (0 / -1 / large positive), Python
``bool`` quirk (``isinstance(True, int) is True``), or cross-loader
key isolation. fo114 closes these in 4 parts / 20 axes (source
unchanged).

Five KEY DIVERGENCES are pinned across the matrix:

* **Distinct keys per loader** -- each loader reads its OWN
 verification subkey. A refactor consolidating into a single shared
 loader with a key parameter could swap keys silently. Parts B / C / D
 cross-check by writing each key alone and proving the SIBLING
 loaders return ``None``.
* **``isinstance(n, int)`` accepts ``bool``** -- ``isinstance(True, int) is True``
 AND ``True >= 1`` so YAML ``true`` for any of the four keys returns
 ``True`` (which equals 1). A "harden against bool leak" refactor
 (``isinstance(n, int) and not isinstance(n, bool)``) would flip
 this. Part D D2 pins it.
* **No upper cap** -- value ``99999`` returns verbatim; only ``< 1``
 is rejected. A "guard against unrealistic thresholds" refactor
 adding ``min(n, 1000)`` would flip Part A A5 and Part D D1.
* **Strict ``int`` check rejects ``2.0`` / ``"2"``** -- only Python
 ``int`` is accepted; YAML floats and string-ints both return
 ``None``. Distinct from
 [``load_anti_deadlock_settings``](packages/hermes_orchestrator/anti_deadlock.py)
 whose ``int(...)`` coerces strings and raises on bad input.
* **Independent file reads** -- each loader opens ``policy.yaml``
 independently; no shared cache. Part D D5 pins call-order
 idempotence.

Four parts:

* **Part A** -- ``load_auto_escalate_after_cumulative_findings``
 defensive arms (file absent / verification non-dict / key missing /
 non-int value / boundary).
* **Part B** -- ``load_notice_escalate_at_cumulative_findings``
 defensive arms + KEY DIVERGENCE vs auto (each-key-alone proof).
* **Part C** -- ``load_escalate_after_cumulative_stage_failures``
 defensive arms + KEY DIVERGENCE vs gate.
* **Part D** -- ``load_escalate_after_cumulative_gate_failures``
 condensed defensive arms + bool-is-int quirk (4-loader sweep) +
 4-key isolation matrix + fault-isolation + call-order idempotence.
"""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)

_POLICY_REL = ("configs", "escalation", "policy.yaml")

_KEY_AUTO = "auto_escalate_after_cumulative_findings"
_KEY_NOTICE = "notice_escalate_at_cumulative_findings"
_KEY_STAGE = "escalate_after_cumulative_stage_failures"
_KEY_GATE = "escalate_after_cumulative_gate_failures"


def _write_policy(repo: Path, body: str) -> Path:
    """Write ``configs/escalation/policy.yaml`` under ``repo``.

    ``exist_ok=True`` so a single test can drop multiple successive
    policy files into the same ``tmp_path`` for sub-axis sweeps.
    Returns the written path so callers can probe ``is_file()``.
    """
    pol_dir = repo / _POLICY_REL[0] / _POLICY_REL[1]
    pol_dir.mkdir(parents=True, exist_ok=True)
    path = pol_dir / _POLICY_REL[2]
    path.write_text(body, encoding="utf-8")
    return path


def test_load_auto_escalate_after_cumulative_findings_defensive_arms_contract(
    tmp_path: Path,
) -> None:
    """Pin ``load_auto_escalate_after_cumulative_findings`` defensive arms (5 axes).

    The function has a 4-arm structure:

    1. ``if not path.is_file(): return None`` -- file-absent.
    2. ``ver = raw.get("verification"); if not isinstance(ver, dict): return None``
       -- verification non-dict.
    3. ``n = ver.get(KEY)`` returns ``None`` when key missing -> falls
       through.
    4. ``if isinstance(n, int) and n >= 1: return n`` -- accept arm;
       anything else returns ``None``.

    The 5 axes here pin every fail-closed branch AND the happy
    boundary for the FIRST loader. Parts B / C / D mirror this shape
    for the other three loaders.

    Each axis uses a fresh ``tmp_path`` subdirectory so writes don't
    cross-contaminate; the file-absent axis depends on a directory
    that has no policy.yaml at all.
    """
    a1_repo = tmp_path / "a1_file_absent"
    a1_repo.mkdir()
    assert load_auto_escalate_after_cumulative_findings(a1_repo) is None, (
        "A1: policy.yaml absent -> `is_file()` fallback returns None. "
        "A refactor that dropped the `is_file` guard would let "
        "`load_yaml` raise FileNotFoundError up to callers"
    )

    non_dict_verification_cases: list[tuple[str, str]] = [
        ("list", "verification:\n  - 1\n  - 2\n"),
        ("scalar_str", 'verification: "not a dict"\n'),
        ("scalar_int", "verification: 5\n"),
        ("explicit_null", "verification: null\n"),
    ]
    for name, body in non_dict_verification_cases:
        repo = tmp_path / f"a2_nondict_{name}"
        repo.mkdir()
        _write_policy(repo, f"version: 1\n{body}")
        actual = load_auto_escalate_after_cumulative_findings(repo)
        assert actual is None, (
            f"A2 {name}: verification non-dict (`{body.strip()}`) -> "
            "`isinstance(ver, dict)` is False -> returns None. "
            f"Got {actual!r}. A refactor swapping `isinstance(ver, dict)` "
            "for a truthiness check would let the list/str cases reach "
            "`ver.get(...)` and raise AttributeError"
        )

    a3_empty_repo = tmp_path / "a3_empty_verification"
    a3_empty_repo.mkdir()
    _write_policy(a3_empty_repo, "version: 1\nverification: {}\n")
    assert load_auto_escalate_after_cumulative_findings(a3_empty_repo) is None, (
        "A3(a): verification is `{}` (empty dict) -> "
        "`ver.get(KEY)` returns None -> fails the `isinstance(n, int)` "
        "check -> returns None. Pins the empty-dict path is distinct "
        "from the non-dict path (A2) but lands at the same return"
    )

    a3_missing_repo = tmp_path / "a3_key_missing"
    a3_missing_repo.mkdir()
    _write_policy(
        a3_missing_repo,
        "version: 1\nverification:\n  unrelated_key: 7\n",
    )
    assert load_auto_escalate_after_cumulative_findings(a3_missing_repo) is None, (
        "A3(b): verification with an unrelated sibling key but no "
        "`auto_escalate_after_cumulative_findings` -> None. Proves the "
        "loader does NOT scrape sibling keys -- a refactor reading the "
        "first int value in verification would FLIP this from None to 7"
    )

    non_int_cases: list[tuple[str, str]] = [
        ("str_two", '"2"'),
        ("float_two", "2.0"),
        ("explicit_null", "null"),
        ("list_value", "[2]"),
    ]
    for name, raw in non_int_cases:
        repo = tmp_path / f"a4_nonint_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_AUTO}: {raw}\n",
        )
        actual = load_auto_escalate_after_cumulative_findings(repo)
        assert actual is None, (
            f"A4 {name}: value `{raw}` is not a Python int -> "
            f"`isinstance(n, int)` is False -> returns None. Got {actual!r}. "
            "KEY DIVERGENCE vs load_anti_deadlock_settings whose "
            "`int(...)` would coerce `\"2\"` -> 2 and raise on `null`. "
            "A refactor swapping `isinstance` for `int(n)` would FLIP "
            "the str_two case (None -> 2) and raise TypeError on null"
        )

    boundary_reject_cases: list[tuple[str, int]] = [
        ("zero", 0),
        ("negative_one", -1),
        ("negative_large", -100),
    ]
    for name, value in boundary_reject_cases:
        repo = tmp_path / f"a5_reject_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_AUTO}: {value}\n",
        )
        actual = load_auto_escalate_after_cumulative_findings(repo)
        assert actual is None, (
            f"A5 reject({name}): value {value} fails `n >= 1` guard -> "
            f"returns None. Got {actual!r}. Pins the strict-positive "
            "boundary (a refactor swapping `>= 1` for `>= 0` would FLIP "
            "the zero case from None to 0)"
        )

    boundary_accept_cases: list[tuple[str, int]] = [
        ("one_canonical_floor", 1),
        ("two_typical", 2),
        ("large_no_upper_cap", 99999),
    ]
    for name, value in boundary_accept_cases:
        repo = tmp_path / f"a5_accept_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_AUTO}: {value}\n",
        )
        actual = load_auto_escalate_after_cumulative_findings(repo)
        assert actual == value, (
            f"A5 accept({name}): value {value} satisfies "
            f"`isinstance(int) and >= 1` -> returns {value} verbatim. "
            f"Got {actual!r}. The large case pins NO UPPER CAP -- a "
            "refactor adding `min(n, 1000)` would FLIP this from 99999 "
            "to 1000"
        )


def test_load_notice_escalate_at_cumulative_findings_defensive_and_key_divergence_contract(
    tmp_path: Path,
) -> None:
    """Pin notice loader defensive arms + KEY DIVERGENCE vs auto (5 axes).

    Mirrors Part A's shape on the SECOND loader -- the loader without
    a prior direct unit test (only ``patch``ed in fo86's emitter
    quartet integration tests). The 5 axes:

    * B1 -- file-absent (mirror of A1).
    * B2 -- verification non-dict (representative; defensive-arm
      shape is identical to A2 so we sample rather than exhaust).
    * B3 -- key missing + non-int value (combined).
    * B4 -- boundary (0 reject, 1 accept floor, 42 accept verbatim).
    * B5 -- KEY DIVERGENCE: writing ONLY the auto key proves the
      notice loader returns None (does not read auto's key); writing
      ONLY the notice key proves the auto loader returns None.
    """
    b1_repo = tmp_path / "b1_file_absent"
    b1_repo.mkdir()
    assert load_notice_escalate_at_cumulative_findings(b1_repo) is None, (
        "B1: policy.yaml absent -> None. Mirrors A1 on the SECOND "
        "loader (which had no direct unit test before fo114)"
    )

    b2_repo = tmp_path / "b2_verification_non_dict"
    b2_repo.mkdir()
    _write_policy(b2_repo, "version: 1\nverification: 7\n")
    assert load_notice_escalate_at_cumulative_findings(b2_repo) is None, (
        "B2: verification as scalar int -> None. Representative "
        "non-dict sample; the full non-dict matrix is in A2"
    )

    b3_missing_repo = tmp_path / "b3_key_missing"
    b3_missing_repo.mkdir()
    _write_policy(
        b3_missing_repo,
        "version: 1\nverification:\n  other_key: 9\n",
    )
    assert load_notice_escalate_at_cumulative_findings(b3_missing_repo) is None, (
        "B3(a): notice key missing while sibling other_key present "
        "-> None. Pins per-key extraction (no first-int-scan)"
    )

    b3_nonint_repo = tmp_path / "b3_value_non_int"
    b3_nonint_repo.mkdir()
    _write_policy(
        b3_nonint_repo,
        f'version: 1\nverification:\n  {_KEY_NOTICE}: "2"\n',
    )
    assert load_notice_escalate_at_cumulative_findings(b3_nonint_repo) is None, (
        "B3(b): notice value is string `\"2\"` -> `isinstance(int)` "
        "False -> None. KEY DIVERGENCE pin vs `int()`-coerce refactor"
    )

    boundary_cases: list[tuple[str, int, int | None]] = [
        ("zero_reject", 0, None),
        ("one_accept_floor", 1, 1),
        ("forty_two_accept_verbatim", 42, 42),
    ]
    for name, value, expected in boundary_cases:
        repo = tmp_path / f"b4_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_NOTICE}: {value}\n",
        )
        actual = load_notice_escalate_at_cumulative_findings(repo)
        assert actual == expected, (
            f"B4 {name}: value {value} -> expected {expected!r}, got "
            f"{actual!r}. Mirrors A5 boundary on the notice loader to "
            "prove its boundary contract matches auto's (a refactor "
            "changing one loader's `>= 1` would break only one half "
            "of this matrix -- co-locating both pins parity)"
        )

    b5_only_auto = tmp_path / "b5_only_auto"
    b5_only_auto.mkdir()
    _write_policy(
        b5_only_auto,
        f"version: 1\nverification:\n  {_KEY_AUTO}: 10\n",
    )
    notice_when_only_auto = load_notice_escalate_at_cumulative_findings(b5_only_auto)
    auto_when_only_auto = load_auto_escalate_after_cumulative_findings(b5_only_auto)
    assert notice_when_only_auto is None, (
        "B5 KEY DIVERGENCE(a): file with ONLY the auto key set to 10 "
        "-> notice loader returns None (it does NOT fall back to "
        f"auto's key). Got {notice_when_only_auto!r}. A refactor "
        "consolidating the two findings loaders to a single shared "
        "function reading the first present key would FLIP this from "
        "None to 10"
    )
    assert auto_when_only_auto == 10, (
        "B5 KEY DIVERGENCE(a-pair): same file -> auto loader returns "
        f"10 verbatim. Got {auto_when_only_auto!r}. Pair with above "
        "to prove the loaders read DISTINCT keys, not just one"
    )

    b5_only_notice = tmp_path / "b5_only_notice"
    b5_only_notice.mkdir()
    _write_policy(
        b5_only_notice,
        f"version: 1\nverification:\n  {_KEY_NOTICE}: 20\n",
    )
    notice_when_only_notice = load_notice_escalate_at_cumulative_findings(b5_only_notice)
    auto_when_only_notice = load_auto_escalate_after_cumulative_findings(b5_only_notice)
    assert notice_when_only_notice == 20, (
        "B5 KEY DIVERGENCE(b): file with ONLY notice key set to 20 "
        f"-> notice loader returns 20 verbatim. Got {notice_when_only_notice!r}"
    )
    assert auto_when_only_notice is None, (
        "B5 KEY DIVERGENCE(b-pair): same file -> auto loader returns "
        f"None (does NOT read notice's key). Got {auto_when_only_notice!r}. "
        "Symmetric to the (a) case to prove the asymmetry IS the contract"
    )


def test_load_escalate_after_cumulative_stage_failures_defensive_and_key_divergence_contract(
    tmp_path: Path,
) -> None:
    """Pin stage loader defensive arms + KEY DIVERGENCE vs gate (5 axes).

    Mirrors Part B's shape on the THIRD loader (the stage-failure
    half of the failures pair). The 5 axes:

    * C1 -- file-absent.
    * C2 -- verification non-dict (representative).
    * C3 -- key missing + non-int value (combined).
    * C4 -- boundary (0 reject, 1 accept, 7 accept verbatim).
    * C5 -- KEY DIVERGENCE: stage and gate loaders read DISTINCT keys
      (proof via each-key-alone writes).
    """
    c1_repo = tmp_path / "c1_file_absent"
    c1_repo.mkdir()
    assert load_escalate_after_cumulative_stage_failures(c1_repo) is None, (
        "C1: policy.yaml absent -> None on stage loader"
    )

    c2_repo = tmp_path / "c2_verification_non_dict"
    c2_repo.mkdir()
    _write_policy(c2_repo, "version: 1\nverification:\n  - a\n  - b\n")
    assert load_escalate_after_cumulative_stage_failures(c2_repo) is None, (
        "C2: verification as list -> None. Representative non-dict "
        "sample; complement to B2's scalar-int case"
    )

    c3_missing_repo = tmp_path / "c3_key_missing"
    c3_missing_repo.mkdir()
    _write_policy(
        c3_missing_repo,
        "version: 1\nverification:\n  unrelated: 11\n",
    )
    assert load_escalate_after_cumulative_stage_failures(c3_missing_repo) is None, (
        "C3(a): stage key missing -> None"
    )

    c3_nonint_repo = tmp_path / "c3_value_non_int"
    c3_nonint_repo.mkdir()
    _write_policy(
        c3_nonint_repo,
        f"version: 1\nverification:\n  {_KEY_STAGE}: 3.0\n",
    )
    assert load_escalate_after_cumulative_stage_failures(c3_nonint_repo) is None, (
        "C3(b): stage value is float `3.0` -> `isinstance(int)` False "
        "-> None. KEY DIVERGENCE pin: a refactor using "
        "`isinstance(n, (int, float))` would accept 3.0 -- this axis "
        "catches it"
    )

    boundary_cases: list[tuple[str, int, int | None]] = [
        ("zero_reject", 0, None),
        ("one_accept_floor", 1, 1),
        ("seven_accept_verbatim", 7, 7),
    ]
    for name, value, expected in boundary_cases:
        repo = tmp_path / f"c4_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_STAGE}: {value}\n",
        )
        actual = load_escalate_after_cumulative_stage_failures(repo)
        assert actual == expected, (
            f"C4 {name}: value {value} -> expected {expected!r}, got "
            f"{actual!r}. Pins stage loader's boundary parity with "
            "auto (A5) and notice (B4)"
        )

    c5_only_stage = tmp_path / "c5_only_stage"
    c5_only_stage.mkdir()
    _write_policy(
        c5_only_stage,
        f"version: 1\nverification:\n  {_KEY_STAGE}: 4\n",
    )
    stage_when_only_stage = load_escalate_after_cumulative_stage_failures(c5_only_stage)
    gate_when_only_stage = load_escalate_after_cumulative_gate_failures(c5_only_stage)
    assert stage_when_only_stage == 4, (
        "C5 KEY DIVERGENCE(a): file with ONLY stage key=4 -> stage "
        f"loader returns 4. Got {stage_when_only_stage!r}"
    )
    assert gate_when_only_stage is None, (
        "C5 KEY DIVERGENCE(a-pair): same file -> gate loader returns "
        f"None. Got {gate_when_only_stage!r}. A refactor consolidating "
        "the stage + gate failure-counter loaders to share a key "
        "would FLIP this"
    )

    c5_only_gate = tmp_path / "c5_only_gate"
    c5_only_gate.mkdir()
    _write_policy(
        c5_only_gate,
        f"version: 1\nverification:\n  {_KEY_GATE}: 5\n",
    )
    stage_when_only_gate = load_escalate_after_cumulative_stage_failures(c5_only_gate)
    gate_when_only_gate = load_escalate_after_cumulative_gate_failures(c5_only_gate)
    assert stage_when_only_gate is None, (
        "C5 KEY DIVERGENCE(b): file with ONLY gate key=5 -> stage "
        f"loader returns None. Got {stage_when_only_gate!r}"
    )
    assert gate_when_only_gate == 5, (
        "C5 KEY DIVERGENCE(b-pair): same file -> gate loader returns "
        f"5 verbatim. Got {gate_when_only_gate!r}. Symmetric to (a)"
    )


def test_escalation_threshold_quartet_cross_loader_matrix_contract(
    tmp_path: Path,
) -> None:
    """Pin gate loader own defensive + bool-is-int quirk + 4-way cross-loader matrix (5 axes).

    The 5 axes lock the gate loader's defensive shape (D1) AND three
    cross-loader properties (D2 bool quirk on ALL four / D3 isolation
    matrix / D4 fault isolation / D5 call-order idempotence) that
    only the FULL quartet can prove.

    The bool-is-int quirk (D2) is the most operator-surprising axis:
    a YAML editor writing ``true`` for an integer threshold key
    silently passes the loader's ``isinstance(n, int)`` guard
    (because ``bool`` is a subclass of ``int`` in Python) and
    ``True >= 1`` is also True, so the loader returns ``True`` (which
    equals 1). A refactor adding
    ``not isinstance(n, bool)`` to the guard would flip every D2
    sub-case and is exactly what an operator might add when "tightening"
    the threshold contract.
    """
    d1_absent = tmp_path / "d1_absent"
    d1_absent.mkdir()
    assert load_escalate_after_cumulative_gate_failures(d1_absent) is None, (
        "D1(absent): policy.yaml absent -> None on gate loader"
    )

    d1_nondict = tmp_path / "d1_nondict"
    d1_nondict.mkdir()
    _write_policy(d1_nondict, "version: 1\nverification: 99\n")
    assert load_escalate_after_cumulative_gate_failures(d1_nondict) is None, (
        "D1(nondict): verification scalar -> None"
    )

    d1_missing = tmp_path / "d1_missing"
    d1_missing.mkdir()
    _write_policy(
        d1_missing,
        "version: 1\nverification:\n  unrelated: 13\n",
    )
    assert load_escalate_after_cumulative_gate_failures(d1_missing) is None, (
        "D1(missing): gate key missing -> None"
    )

    d1_nonint = tmp_path / "d1_nonint"
    d1_nonint.mkdir()
    _write_policy(
        d1_nonint,
        f'version: 1\nverification:\n  {_KEY_GATE}: "5"\n',
    )
    assert load_escalate_after_cumulative_gate_failures(d1_nonint) is None, (
        "D1(nonint): gate value as string -> None"
    )

    d1_boundary_cases: list[tuple[str, int, int | None]] = [
        ("zero_reject", 0, None),
        ("one_accept", 1, 1),
        ("two_accept", 2, 2),
    ]
    for name, value, expected in d1_boundary_cases:
        repo = tmp_path / f"d1_boundary_{name}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {_KEY_GATE}: {value}\n",
        )
        actual = load_escalate_after_cumulative_gate_failures(repo)
        assert actual == expected, (
            f"D1 boundary {name}: value {value} -> expected "
            f"{expected!r}, got {actual!r}. Pins gate loader boundary "
            "parity with the other 3 loaders (A5 / B4 / C4)"
        )

    bool_true_quartet_cases: list[tuple[str, str, object]] = [
        (_KEY_AUTO, "auto", load_auto_escalate_after_cumulative_findings),
        (_KEY_NOTICE, "notice", load_notice_escalate_at_cumulative_findings),
        (_KEY_STAGE, "stage", load_escalate_after_cumulative_stage_failures),
        (_KEY_GATE, "gate", load_escalate_after_cumulative_gate_failures),
    ]
    for yaml_key, label, loader in bool_true_quartet_cases:
        repo = tmp_path / f"d2_true_{label}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {yaml_key}: true\n",
        )
        actual = loader(repo)  # type: ignore[operator]
        assert actual is True, (
            f"D2 bool-is-int(true, {label}): YAML `true` -> Python "
            "`True` -> `isinstance(True, int)` is True AND `True >= 1` "
            f"is True -> loader returns True. Got {actual!r}. KEY "
            "DIVERGENCE: this is the silent acceptance quirk -- a "
            "refactor adding `not isinstance(n, bool)` to the guard "
            "would FLIP this from True to None for all 4 loaders"
        )

    for yaml_key, label, loader in bool_true_quartet_cases:
        repo = tmp_path / f"d2_false_{label}"
        repo.mkdir()
        _write_policy(
            repo,
            f"version: 1\nverification:\n  {yaml_key}: false\n",
        )
        actual = loader(repo)  # type: ignore[operator]
        assert actual is None, (
            f"D2 bool-is-int(false, {label}): YAML `false` -> Python "
            "`False` -> `isinstance(False, int)` is True BUT `False >= 1` "
            f"is False -> loader returns None. Got {actual!r}. Pairs "
            "with the `true` half to prove the asymmetry IS the "
            "contract (only `true` leaks through, not `false`)"
        )

    d3_repo = tmp_path / "d3_isolation_matrix"
    d3_repo.mkdir()
    _write_policy(
        d3_repo,
        "version: 1\n"
        "verification:\n"
        f"  {_KEY_AUTO}: 2\n"
        f"  {_KEY_NOTICE}: 3\n"
        f"  {_KEY_STAGE}: 4\n"
        f"  {_KEY_GATE}: 5\n",
    )
    d3_auto = load_auto_escalate_after_cumulative_findings(d3_repo)
    d3_notice = load_notice_escalate_at_cumulative_findings(d3_repo)
    d3_stage = load_escalate_after_cumulative_stage_failures(d3_repo)
    d3_gate = load_escalate_after_cumulative_gate_failures(d3_repo)
    assert (d3_auto, d3_notice, d3_stage, d3_gate) == (2, 3, 4, 5), (
        "D3: 4-key isolation matrix -- single policy.yaml with ALL "
        "four keys at DISTINCT values (auto=2, notice=3, stage=4, "
        f"gate=5). Expected (2, 3, 4, 5), got ({d3_auto!r}, "
        f"{d3_notice!r}, {d3_stage!r}, {d3_gate!r}). Each loader "
        "returns its OWN key's value with NO cross-contamination. A "
        "refactor that swapped any two keys would surface as exactly "
        "ONE mismatched position in this tuple"
    )

    d4_repo = tmp_path / "d4_fault_isolation"
    d4_repo.mkdir()
    _write_policy(
        d4_repo,
        "version: 1\n"
        "verification:\n"
        f"  {_KEY_AUTO}: 2\n"
        f'  {_KEY_NOTICE}: "abc"\n'
        f"  {_KEY_STAGE}: 4\n"
        f"  {_KEY_GATE}: 5\n",
    )
    d4_auto = load_auto_escalate_after_cumulative_findings(d4_repo)
    d4_notice = load_notice_escalate_at_cumulative_findings(d4_repo)
    d4_stage = load_escalate_after_cumulative_stage_failures(d4_repo)
    d4_gate = load_escalate_after_cumulative_gate_failures(d4_repo)
    assert d4_notice is None, (
        "D4(corrupted): notice key set to string `\"abc\"` -> notice "
        f"loader returns None. Got {d4_notice!r}"
    )
    assert (d4_auto, d4_stage, d4_gate) == (2, 4, 5), (
        "D4(siblings): the 3 OTHER loaders still return their valid "
        f"values despite notice's corruption. Expected (2, 4, 5), got "
        f"({d4_auto!r}, {d4_stage!r}, {d4_gate!r}). Pins per-loader "
        "fault isolation -- a refactor that short-circuited the "
        "shared `load_yaml` call across loaders (e.g. cached + raised "
        "on first bad value) would FLIP all 3 to None"
    )

    d5_repo = tmp_path / "d5_call_order"
    d5_repo.mkdir()
    _write_policy(
        d5_repo,
        "version: 1\n"
        "verification:\n"
        f"  {_KEY_AUTO}: 11\n"
        f"  {_KEY_NOTICE}: 22\n"
        f"  {_KEY_STAGE}: 33\n"
        f"  {_KEY_GATE}: 44\n",
    )
    forward = (
        load_auto_escalate_after_cumulative_findings(d5_repo),
        load_notice_escalate_at_cumulative_findings(d5_repo),
        load_escalate_after_cumulative_stage_failures(d5_repo),
        load_escalate_after_cumulative_gate_failures(d5_repo),
    )
    reverse = (
        load_escalate_after_cumulative_gate_failures(d5_repo),
        load_escalate_after_cumulative_stage_failures(d5_repo),
        load_notice_escalate_at_cumulative_findings(d5_repo),
        load_auto_escalate_after_cumulative_findings(d5_repo),
    )
    interleaved = (
        load_auto_escalate_after_cumulative_findings(d5_repo),
        load_auto_escalate_after_cumulative_findings(d5_repo),
        load_notice_escalate_at_cumulative_findings(d5_repo),
        load_escalate_after_cumulative_stage_failures(d5_repo),
        load_escalate_after_cumulative_gate_failures(d5_repo),
        load_escalate_after_cumulative_gate_failures(d5_repo),
    )
    assert forward == (11, 22, 33, 44), (
        f"D5(forward): forward call order returns (11, 22, 33, 44), "
        f"got {forward!r}"
    )
    assert reverse == (44, 33, 22, 11), (
        f"D5(reverse): reverse call order returns (44, 33, 22, 11), "
        f"got {reverse!r}. Pins that loader order does NOT affect "
        "each loader's own return"
    )
    assert interleaved == (11, 11, 22, 33, 44, 44), (
        f"D5(interleaved): repeated calls return identical values, "
        f"got {interleaved!r}. Pins idempotence -- a refactor that "
        "introduced module-level caching keyed on first-read state "
        "would break here"
    )
