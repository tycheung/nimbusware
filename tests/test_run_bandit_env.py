"""``HERMES_RUN_BANDIT`` env-layer string-arm contract (follow-on 66, §14 #18).

[`run_bandit`](d:\\Hermes\\packages\\hermes_orchestrator\\verifiers.py) reads
``HERMES_RUN_BANDIT`` via ``os.environ.get(...).lower() not in ("1", "true",
"yes")``. This is the **first inverted Pattern A** binary gate pinned by the
fo62-65 env-layer sweep: truthy variants **enable** real bandit, every other
value (including whitespace-padded canonical, the asymmetric YAML token
``"on"``, falsy-look values, empty / junk) returns the operator-facing skip
tuple. Before this slice no test file mentioned the env, so the full
string-arm matrix was unpinned.

Three parts:

* **Part A** locks the truthy tuple membership (env-gate accepted -> reaches
  the ``shutil.which`` branch which we mock to None for determinism).
* **Part B** locks the **exact** operator-facing skip message
  ``(0, "bandit skipped (set HERMES_RUN_BANDIT=1 to enable)\\n")`` so a
  refactor that drifts the exit code, the trailing newline, or the
  ``HERMES_RUN_BANDIT=1`` hint fails loudly.
* **Part C** locks the asymmetric fail-closed string-arm (whitespace-padded,
  ``"on"`` / ``"ON"``, case-folded falsy, empty / junk / near-miss / interior
  whitespace) -- parallel to fo65 Part C.

Per-case messages ``force_on raw=<raw>`` / ``skip_message raw=<raw>`` /
``fail_closed raw=<raw>`` identify the failing branch + offending env scalar.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_orchestrator.verifiers import run_bandit

_ENV_GATE_SKIP: tuple[int, str] = (
    0,
    "bandit skipped (set HERMES_RUN_BANDIT=1 to enable)\n",
)
_PATH_MISSING_SKIP: tuple[int, str] = (0, "bandit not on PATH; skipped\n")


def test_run_bandit_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pin §14 #18 ``HERMES_RUN_BANDIT`` force-on truthy tuple membership.

    The env-gate at [verifiers.py:36](d:\\Hermes\\packages\\hermes_orchestrator\\verifiers.py)
    uses ``not in ("1", "true", "yes")`` so truthy variants reach the
    downstream ``shutil.which("bandit")`` branch. Patching ``shutil.which``
    to ``None`` collapses that branch to a deterministic
    ``_PATH_MISSING_SKIP`` return regardless of whether bandit is installed
    on the test host.

    If the env-gate had rejected the variant (e.g. someone broke
    ``.lower()`` or shrank the tuple to ``("1", "true")``), the result
    would be ``_ENV_GATE_SKIP`` instead and the assertion would fail with
    a clear per-case message identifying the offending env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("HERMES_RUN_BANDIT", raw)
        with patch(
            "hermes_orchestrator.verifiers.shutil.which",
            return_value=None,
        ):
            result = run_bandit(tmp_path)
        assert result == _PATH_MISSING_SKIP, f"force_on raw={raw!r}"


def test_run_bandit_env_skip_message_format_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pin §14 #18 operator-facing skip message text exactly.

    The skip tuple ``(0, "bandit skipped (set HERMES_RUN_BANDIT=1 to
    enable)\\n")`` is documented operator output -- a refactor that
    changes the exit code, drops the trailing newline, or alters the
    ``HERMES_RUN_BANDIT=1`` hint (e.g. to ``HERMES_RUN_BANDIT=true``)
    silently breaks operator runbooks.

    Four canonical fail-closed cases cover the "documented falsy" inputs
    operators are likeliest to pass: env unset (the production default),
    ``"0"``, ``"false"``, ``"no"``. Each must return ``_ENV_GATE_SKIP``
    exactly.

    Distinct from Part C: Part B locks the **message text**, Part C
    locks the **coercion contract** for asymmetric / whitespace / edge
    inputs (both yield ``_ENV_GATE_SKIP`` but for different reasons).
    """
    cases: list[tuple[str, str | None]] = [
        ("env_absent", None),
        ("falsy_zero", "0"),
        ("falsy_false", "false"),
        ("falsy_no", "no"),
    ]
    for _name, raw in cases:
        if raw is None:
            monkeypatch.delenv("HERMES_RUN_BANDIT", raising=False)
        else:
            monkeypatch.setenv("HERMES_RUN_BANDIT", raw)
        result = run_bandit(tmp_path)
        assert result == _ENV_GATE_SKIP, f"skip_message raw={raw!r}"


def test_run_bandit_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pin §14 #18 asymmetric fail-closed string-arm at the inverted gate.

    Loops 11 fail-closed variants spanning four sub-contracts (parallel
    to follow-on 65 Part C for ``HERMES_OUTBOUND_FETCH_ENABLED``):

    1. **No ``.strip()``** -- whitespace-padded canonical
       (``"  1  "`` / ``" true "`` / ``"\\tyes\\n"``) fail-closed
       because ``.lower()`` alone does not trim whitespace. A future
       refactor adding ``.strip()`` to "match the YAML coercer" silently
       flips ``" 1 "`` from "skip" to "enable real bandit" -- this test
       fails loudly on exactly that change.
    2. **``"on"`` / ``"off"`` asymmetry** vs YAML coercer -- the env
       layer excludes ``"on"`` from the truthy tuple even though the
       workflow YAML coercer accepts it (parallel to fo51 / fo62 /
       fo63 / fo64 / fo65).
    3. **Single-tuple membership** -- case-folded falsy (``"FALSE"`` /
       ``"NO"``) and unknown tokens both fail-closed via the same
       ``not in`` predicate (no separate falsy tuple to short-circuit
       through).
    4. **Empty / junk / near-miss / interior whitespace** -- ``""`` /
       ``"maybe"`` / ``"true!"`` / ``" ye s "`` all fall through the
       ``not in`` check.

    Distinct from Part B: Part B locks the exact operator message text
    via four "obvious" falsy inputs; Part C locks the coercion contract
    via inputs designed to trip a careless unification refactor.
    """
    cases: list[tuple[str, str]] = [
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("yaml_on_lower", "on"),
        ("yaml_on_upper", "ON"),
        ("upper_false", "FALSE"),
        ("upper_no", "NO"),
        ("empty", ""),
        ("junk_maybe", "maybe"),
        ("near_miss_true_bang", "true!"),
        ("interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("HERMES_RUN_BANDIT", raw)
        result = run_bandit(tmp_path)
        assert result == _ENV_GATE_SKIP, f"fail_closed raw={raw!r}"
