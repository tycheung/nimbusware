"""§14 #17: workflow YAML can opt in to self_refinement stage marker."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path

from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_parse_self_refinement_workflow_block_repo_profile() -> None:
    b = parse_self_refinement_workflow_block(ROOT, "self_refinement_on")
    assert b.enabled is True
    assert b.version == 1
    assert b.description is not None and "§14" in b.description


def test_parse_self_refinement_workflow_max_iterations_and_auto_promote(tmp_path: Path) -> None:
    _write_self_refinement_profile(
        tmp_path,
        "sr_depth",
        "version: 1\nself_refinement:\n  enabled: true\n"
        "  max_iterations: 7\n  auto_promote_probation: true\n",
    )
    block = parse_self_refinement_workflow_block(tmp_path, "sr_depth")
    assert block.max_iterations == 7
    assert block.auto_promote_probation is True


def test_emit_self_refinement_marker_when_workflow_enables() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("self_refinement_on")
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    rows = mem.list_run_events(str(rid))
    markers = [
        r
        for r in rows
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    ]
    assert len(markers) == 1
    meta = (markers[0].get("metadata") or {}).get("self_refinement") or {}
    assert meta.get("version") == 1
    assert isinstance(meta.get("description"), str)


def test_self_refinement_marker_off_for_default_when_policy_disabled() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    rows = mem.list_run_events(str(rid))
    assert not any(
        (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
        for r in rows
        if r.get("event_type") == "stage.started"
    )


def _write_self_refinement_profile(repo: Path, name: str, body: str) -> None:
    """Write ``configs/workflows/{name}.yaml`` under ``repo`` with the given body.

    Mirrors the ``_write_profile`` style in ``tests/test_workflow_security_metadata.py``
    but uses ``exist_ok=True`` so a single test can drop many per-case profiles into the
    same tmp directory without re-creating fixture scaffolding.
    """
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_parse_self_refinement_malformed_block_yields_defaults(
    tmp_path: Path,
) -> None:
    """Pin §14 #17: scalar/list ``self_refinement:`` block → defaults.

    The ``if not isinstance(block, dict)`` early-return in
    :func:`parse_self_refinement_workflow_block` is the safety net for operator typos
    like ``self_refinement: true`` or ``self_refinement: []``. Lock both shapes so any
    refactor that wants to accept e.g. scalar shortcuts must update this test on
    purpose. Mirrors the malformed-shape style of follow-on 52
    (``test_parse_escalation_malformed_root_or_block_yields_defaults``).
    """
    _write_self_refinement_profile(
        tmp_path, "block_scalar", "version: 1\nself_refinement: true\n",
    )
    _write_self_refinement_profile(
        tmp_path, "block_list", "version: 1\nself_refinement: []\n",
    )
    for name in ("block_scalar", "block_list"):
        block = parse_self_refinement_workflow_block(tmp_path, name)
        assert block == SelfRefinementWorkflowBlock(), name


def test_parse_self_refinement_field_coercion_contract(tmp_path: Path) -> None:
    """Pin ``enabled`` / ``version`` / ``description`` coercion ladders (§14 #17).

    ``enabled`` is coerced via plain ``bool(...)`` which **diverges** from
    ``_coerce_yaml_bool`` (used by sibling parsers): ``bool("false")`` is ``True``
    because the string is non-empty, while ``_coerce_yaml_bool("false")`` is ``False``.
    ``version`` uses ``int(...)`` with ``TypeError`` / ``ValueError`` caught (so
    ``"abc"`` and ``null`` return ``None``; a float like ``1.5`` narrows to ``1``).
    ``description`` is kept only when ``isinstance(str)`` AND ``.strip()`` is truthy.
    This single test locks all three contracts so a future refactor that aligns them
    with sibling parsers breaks exactly the cases that changed.
    """
    enabled_cases: list[tuple[str, str, bool]] = [
        ("en_bool_true", "true", True),
        ("en_bool_false", "false", False),
        ("en_int_zero", "0", False),
        ("en_str_false_quoted", '"false"', True),
        ("en_missing", "", False),
    ]
    for name, raw, expected in enabled_cases:
        body = (
            "version: 1\nself_refinement:\n  version: 1\n"
            if name == "en_missing"
            else f"version: 1\nself_refinement:\n  enabled: {raw}\n"
        )
        _write_self_refinement_profile(tmp_path, name, body)
        block = parse_self_refinement_workflow_block(tmp_path, name)
        assert block.enabled is expected, name

    version_cases: list[tuple[str, str, int | None]] = [
        ("ver_int", "1", 1),
        ("ver_str_digit", '"1"', 1),
        ("ver_float_narrow", "1.5", 1),
        ("ver_bad_str", '"abc"', None),
        ("ver_null", "null", None),
    ]
    for name, raw, expected in version_cases:
        body = f"version: 1\nself_refinement:\n  enabled: true\n  version: {raw}\n"
        _write_self_refinement_profile(tmp_path, name, body)
        block = parse_self_refinement_workflow_block(tmp_path, name)
        assert block.version == expected, name

    desc_cases: list[tuple[str, str, str | None]] = [
        ("desc_padded", '"  hello  "', "hello"),
        ("desc_empty", '""', None),
        ("desc_whitespace", '"   "', None),
        ("desc_non_str", "42", None),
        ("desc_missing", "", None),
    ]
    for name, raw, expected in desc_cases:
        body = (
            "version: 1\nself_refinement:\n  enabled: true\n"
            if name == "desc_missing"
            else f"version: 1\nself_refinement:\n  enabled: true\n  description: {raw}\n"
        )
        _write_self_refinement_profile(tmp_path, name, body)
        block = parse_self_refinement_workflow_block(tmp_path, name)
        assert block.description == expected, name


def test_self_refinement_enabled_bool_ladder_boundary_cases(tmp_path: Path) -> None:
    """Pin §14 #17 ``enabled`` ``bool()``-ladder boundary contract.

    :func:`parse_self_refinement_workflow_block` coerces ``enabled`` via plain
    ``bool(block.get("enabled", False))`` — Python's built-in truthiness — which
    **diverges** from the tuple ladder used by ``_coerce_yaml_bool``
    (universal_critique), :func:`parse_escalation_workflow_block`, and
    :func:`_coerce_security_scan_metadata_enabled_value`. Follow-on 53 pinned a
    single representative ``"false"`` divergence; this test locks the **full
    boundary surface** so any future refactor unifying the ladders breaks
    multiple cases here with per-case ``case_id`` messages.

    The two ``bool()``-ladder parsers (self_refinement, agent_evaluator) must
    share this contract — Part B in
    :func:`tests/test_workflow_agent_evaluator.py::test_agent_evaluator_enabled_bool_ladder_boundary_cases`
    locks the same 12-case table against the sibling parser.

    Note that ``yaml_null`` flows through ``block.get("enabled", False)`` as
    ``None`` (key present, value ``None``) rather than the missing-key default;
    ``bool(None)`` is False. All string variants are quoted so PyYAML's YAML 1.1
    bool resolver does not eagerly convert unquoted ``false`` / ``no`` / ``off``
    to Python ``bool`` and bypass the ``bool(str)`` arm.
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str, bool]] = [
        ("empty_str", '""', False),
        ("ws_only_str", '"   "', True),
        ("lower_false", '"false"', True),
        ("upper_false", '"FALSE"', True),
        ("padded_off", '"  off  "', True),
        ("lower_no", '"no"', True),
        ("lower_true", '"true"', True),
        ("yaml_null", "null", False),
        ("empty_list", "[]", False),
        ("nonempty_list", "[a]", True),
        ("empty_dict", "{}", False),
        ("zero_int", "0", False),
    ]
    for name, raw, expected in cases:
        _write_self_refinement_profile(
            repo,
            name,
            f"version: 1\nself_refinement:\n  enabled: {raw}\n",
        )
        block = parse_self_refinement_workflow_block(repo, name)
        assert block.enabled is expected, f"enabled={raw}"
