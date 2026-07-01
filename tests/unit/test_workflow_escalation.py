from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.workflow_blocks_simple import (
    EscalationWorkflowBlock,
    parse_escalation_workflow_block,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_parse_escalation_default_profile_off() -> None:
    block = parse_escalation_workflow_block(ROOT, "default")
    assert block == EscalationWorkflowBlock(suppress_automatic_escalation=False)


def test_parse_escalation_suppress_profile_on() -> None:
    block = parse_escalation_workflow_block(ROOT, "escalation_suppress_on")
    assert block.suppress_automatic_escalation is True


def test_parse_escalation_missing_profile() -> None:
    assert parse_escalation_workflow_block(ROOT, None) == EscalationWorkflowBlock()


def test_parse_escalation_malformed_root_or_block_yields_defaults(
    tmp_path: Path,
) -> None:
    """Pin §14 #19: scalar/list ``escalation`` block or unknown string value → defaults.

    Both malformed-block guards in :func:`parse_escalation_workflow_block`
    (``block = raw.get("escalation") if isinstance(raw, dict) else None`` and
    ``if not isinstance(block, dict)``) collapse to a default
    :class:`EscalationWorkflowBlock` (``suppress=False``) so any refactor that wants to
    accept a top-level scalar or non-dict ``escalation:`` must update this test on
    purpose. Mirrors the malformed-shape style of follow-on 18 in
    :func:`test_parse_universal_critique_root_scalar_or_list_yields_defaults`.
    """
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "scalar_root.yaml").write_text(
        "version: 1\nescalation: true\n",
        encoding="utf-8",
    )
    (wf_dir / "list_root.yaml").write_text(
        "version: 1\nescalation: []\n",
        encoding="utf-8",
    )
    (wf_dir / "block_scalar.yaml").write_text(
        'version: 1\nescalation:\n  suppress_automatic_escalation: "boom"\n',
        encoding="utf-8",
    )
    for name in ("scalar_root", "list_root", "block_scalar"):
        block = parse_escalation_workflow_block(repo, name)
        assert block == EscalationWorkflowBlock(), name


def test_parse_escalation_suppress_value_coercion(tmp_path: Path) -> None:
    """Pin the full ``suppress_automatic_escalation`` coercion contract (§14 #19).

    Covers every branch of the coercion ladder in
    :func:`parse_escalation_workflow_block`: ``bool`` passthrough, numeric truthiness
    (``int`` / ``float`` via ``bool()``), the case-insensitive whitespace-trimmed string
    truthy tuple (``"1" / "true" / "yes" / "on"``), and the unknown-type fallthrough
    returning ``False`` for ``None`` / ``list`` / ``dict`` values. Locks the contract so a
    future refactor (e.g. unifying with ``_coerce_yaml_bool`` from
    ``workflow_universal_critique``) must update this test on purpose. String YAML
    literals are quoted so PyYAML never folds them into a bool via YAML 1.1 conventions
    (``yes`` / ``no`` / ``on`` / ``off`` unquoted).
    """
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)

    cases: list[tuple[str, str, bool]] = [
        ("bool_true", "true", True),
        ("bool_false", "false", False),
        ("int_one", "1", True),
        ("int_zero", "0", False),
        ("float_truthy", "1.5", True),
        ("str_yes_caps", '"  YES  "', True),
        ("str_on", '"on"', True),
        ("str_off", '"off"', False),
        ("str_junk", '"junk"', False),
        ("null_val", "null", False),
        ("list_val", "[a, b]", False),
        ("dict_val", "{nested: true}", False),
    ]
    for name, raw_yaml, expected in cases:
        (wf_dir / f"{name}.yaml").write_text(
            f"version: 1\nescalation:\n  suppress_automatic_escalation: {raw_yaml}\n",
            encoding="utf-8",
        )
        block = parse_escalation_workflow_block(repo, name)
        assert block.suppress_automatic_escalation is expected, name


def test_escalation_suppress_string_case_whitespace_round_trip(
    tmp_path: Path,
) -> None:
    """Pin §14 #19 ``suppress_automatic_escalation`` tuple-ladder case + whitespace round-trip.

    :func:`parse_escalation_workflow_block` coerces the string arm via
    ``raw.strip().lower() in ("1", "true", "yes", "on")`` — same shape as
    ``_coerce_yaml_bool`` in :mod:`workflow_universal_critique`. Follow-on 52
    covered canonical lowercase tokens (``"on"``, ``"off"``, ``"junk"``) plus a
    single ``"  YES  "`` case-folded + whitespace variant; this test extends the
    coverage to the **full mixed-case + whitespace + falsy + near-miss surface**
    mirroring the three-axis breakdown that follow-on 59 pinned for
    ``_coerce_yaml_bool``:

    1. ``.lower()`` case-folding for every truthy token (``"TRUE"`` / ``"Yes"``
       / ``"ON"`` / ``"yEs"``).
    2. ``.strip()`` whitespace handling including tab / newline edges
       (``"\\ttrue\\n"`` / ``"  ON  "``).
    3. Exclusive-membership negative branch (case-folded ``"FALSE"`` /
       ``"  OFF  "`` / ``"NO"``, near-miss ``"true!"`` extra char, interior
       whitespace ``" ye s "`` that ``.strip()`` cannot rescue, stripped-to-empty
       ``"   "`` and ``""``).

    Part of follow-on 60 alongside Parts A / B (``bool()`` ladder for
    self_refinement / agent_evaluator); this Part C locks the divergent
    tuple-ladder branch. All scalars are **quoted** so PyYAML's YAML 1.1 bool
    resolver does not eagerly convert unquoted ``TRUE`` / ``Yes`` / ``On`` /
    ``NO`` to Python ``bool`` and bypass the string arm — same caveat
    documented in follow-on 59.
    """
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    cases: list[tuple[str, str, bool]] = [
        ("upper_true", '"TRUE"', True),
        ("title_yes", '"Yes"', True),
        ("upper_on_padded", '"  ON  "', True),
        ("mixed_yes_padded", '"  yEs  "', True),
        ("tab_true_lf", '"\\ttrue\\n"', True),
        ("upper_false", '"FALSE"', False),
        ("padded_off", '"  OFF  "', False),
        ("upper_no", '"NO"', False),
        ("near_miss_bang", '"true!"', False),
        ("interior_ws_yes", '" ye s "', False),
        ("only_ws", '"   "', False),
        ("empty_quoted", '""', False),
    ]
    for name, raw_yaml, expected in cases:
        (wf_dir / f"{name}.yaml").write_text(
            f"version: 1\nescalation:\n  suppress_automatic_escalation: {raw_yaml}\n",
            encoding="utf-8",
        )
        block = parse_escalation_workflow_block(repo, name)
        assert block.suppress_automatic_escalation is expected, f"suppress={raw_yaml}"
