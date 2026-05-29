"""_repro_steps_from_critique_gate`` direct-contract edges."""


from __future__ import annotations

from typing import Any
from uuid import uuid4

from hermes_orchestrator.pipeline import make_dev_orchestrator


def _base(**extra: Any) -> dict[str, Any]:
    """Minimal valid payload + per-axis overrides (always sets stage + verdict)."""
    return {"stage_name": "x", "verdict": "FAIL", **extra}


def test_repro_steps_failure_reason_code_coalesce_ladder_5_axis() -> None:
    """Pin (gate_pl.get('failure_reason_code') or '').strip() coalesce at pipeline.py:890-892.

    Coverage delta vs fo89 D4c: fo89 only pinned .strip() on a non-empty
    "  spaced  " input. The full coalesce ladder (None -> ""; missing key;
    empty string; whitespace-only -> "" via strip-before-truthy; non-empty
    after strip is what gets appended) is unpinned.
    """
    orch, _ = make_dev_orchestrator()
    repro = orch._repro_steps_from_critique_gate  # noqa: SLF001

    assert repro(_base()) == ["stage=x", "verdict=FAIL"], (
        "A1: failure_reason_code key missing -> .get default None -> "
        "(None or '').strip() = '' -> suppressed -> 2-line output"
    )

    assert repro(_base(failure_reason_code=None)) == ["stage=x", "verdict=FAIL"], (
        "A2: explicit None -> (None or '').strip() = '' -> suppressed; "
        "indistinguishable from missing-key path"
    )

    assert repro(_base(failure_reason_code="")) == ["stage=x", "verdict=FAIL"], (
        "A3: empty string -> ('' or '').strip() = '' -> suppressed via `or ''` short-circuit"
    )

    assert repro(_base(failure_reason_code="   ")) == ["stage=x", "verdict=FAIL"], (
        "A4: whitespace-only '   ' -> ('   ' or '').strip() = '' -> suppressed; "
        "CRITICAL: pins that .strip() runs BEFORE the `if code:` truthy check "
        "so whitespace-only payloads do NOT slip through"
    )

    assert repro(_base(failure_reason_code="\tcode_x\n")) == [
        "stage=x",
        "verdict=FAIL",
        "failure_reason_code=code_x",
    ], (
        "A5: non-empty after strip -> ('\\tcode_x\\n' or '').strip() = 'code_x' -> "
        "included AS THE STRIPPED VALUE (not the raw '\\tcode_x\\n')"
    )


def test_repro_steps_empty_none_non_list_rejection_matrix_5_axis() -> None:
    """Pin isinstance+truthy AND-guards at pipeline.py:893-898.

    Coverage delta vs fo89 D4d: fo89 covers "non-list failing_critics +
    empty failing_finding_ids" in ONE combined axis. fo100 closes the
    reverse asymmetry, the None values, and the dual-empty cross-cut.
    """
    orch, _ = make_dev_orchestrator()
    repro = orch._repro_steps_from_critique_gate  # noqa: SLF001

    assert repro(_base(failing_critics=[])) == ["stage=x", "verdict=FAIL"], (
        "B1: failing_critics=[] empty list -> isinstance True but [] falsy -> "
        "AND-guard fails -> suppressed (distinct from non-list axis already covered)"
    )

    assert repro(_base(failing_critics=None)) == ["stage=x", "verdict=FAIL"], (
        "B2: failing_critics=None -> isinstance(None, list) False -> suppressed"
    )

    assert repro(_base(failing_finding_ids="not-a-list")) == ["stage=x", "verdict=FAIL"], (
        "B3: failing_finding_ids='not-a-list' string -> isinstance(str, list) False -> "
        "suppressed; reverse asymmetry vs fo89 D4d (which had non-list critics + empty ids)"
    )

    assert repro(_base(failing_finding_ids=None)) == ["stage=x", "verdict=FAIL"], (
        "B4: failing_finding_ids=None -> isinstance(None, list) False -> suppressed"
    )

    assert repro(_base(failing_critics=[], failing_finding_ids=[])) == [
        "stage=x",
        "verdict=FAIL",
    ], (
        "B5: dual-empty cross-cut -> both AND-guards fail -> exactly 2 lines; "
        "proves the two empty-list rejections combine cleanly with no leak between guards"
    )


def test_repro_steps_count_line_pluralization_4_axis() -> None:
    """Pin f-string format with `len()` at pipeline.py:895, 898.

    Coverage delta vs fo89 D4b: fo89 only exercises 2 critics + 1 finding.
    fo100 pins the 1-element boundary AND a larger N-element across both
    lists to prove the format uses `len()` directly with literal "(s)"
    suffix (no `if len == 1` pluralization branch).
    """
    orch, _ = make_dev_orchestrator()
    repro = orch._repro_steps_from_critique_gate  # noqa: SLF001

    assert repro(_base(failing_critics=[uuid4()])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_critics=1 critic(s)",
    ], (
        "C1: 1-element critics -> 'failing_critics=1 critic(s)' literal '(s)' suffix; "
        "no pluralization branch (would be 'critic' singular if branched)"
    )

    assert repro(_base(failing_critics=[uuid4() for _ in range(5)])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_critics=5 critic(s)",
    ], (
        "C2: 5-element critics -> 'failing_critics=5 critic(s)' via len() directly; "
        "no special small-list path"
    )

    assert repro(_base(failing_finding_ids=[uuid4()])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_finding_ids=1 id(s)",
    ], (
        "C3: 1-element ids -> 'failing_finding_ids=1 id(s)' literal '(s)' suffix "
        "(symmetric with C1 on critics)"
    )

    assert repro(_base(failing_finding_ids=[uuid4(), uuid4()])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_finding_ids=2 id(s)",
    ], (
        "C4: 2-element ids -> 'failing_finding_ids=2 id(s)' multi-element happy path "
        "(symmetric with C2 on critics)"
    )


def test_repro_steps_subset_of_optionals_ordering_and_truncation_cap_5_axis() -> None:
    """Pin subset-of-optionals ordering + defensive [:40] cap at pipeline.py:886-899.

    Coverage delta vs fo89 D4b: fo89 only covers "all 3 optionals present";
    the 5 subset combinations and the truncation cap are unpinned.
    """
    orch, _ = make_dev_orchestrator()
    repro = orch._repro_steps_from_critique_gate  # noqa: SLF001

    assert repro(_base(failure_reason_code="code_x")) == [
        "stage=x",
        "verdict=FAIL",
        "failure_reason_code=code_x",
    ], "D1: only failure_reason_code -> 3-line output with code in slot 3"

    assert repro(_base(failing_critics=[uuid4(), uuid4()])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_critics=2 critic(s)",
    ], "D2: only failing_critics -> 3-line output with critics in slot 3"

    assert repro(_base(failing_finding_ids=[uuid4(), uuid4(), uuid4()])) == [
        "stage=x",
        "verdict=FAIL",
        "failing_finding_ids=3 id(s)",
    ], "D3: only failing_finding_ids -> 3-line output with ids in slot 3"

    assert repro(
        _base(
            failure_reason_code="code_x",
            failing_finding_ids=[uuid4(), uuid4()],
        ),
    ) == [
        "stage=x",
        "verdict=FAIL",
        "failure_reason_code=code_x",
        "failing_finding_ids=2 id(s)",
    ], (
        "D4: code + ids but NO critics -> 4-line output; CRITICAL: pins that "
        "critics omission collapses naturally (ids slot follows code DIRECTLY, "
        "no empty placeholder slot for critics)"
    )

    full = repro(
        _base(
            failure_reason_code="code_x",
            failing_critics=[uuid4(), uuid4()],
            failing_finding_ids=[uuid4()],
        ),
    )
    assert len(full) == 5, "D5: full 5-line payload -> exactly 5 lines"
    assert full == full[:40], (
        "D5: defensive [:40] truncation cap; 5 < 40 so result == result[:40]; "
        "pins that the cap is never hit by the current logic and protects against "
        "future expansion that might add more optional segments"
    )
