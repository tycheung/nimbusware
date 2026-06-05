"""workflow ``agent_evaluator`` block parsing."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorWorkflowBlock,
    parse_agent_evaluator_workflow_block,
)
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_parse_agent_evaluator_default_profile_disabled() -> None:
    block = parse_agent_evaluator_workflow_block(ROOT, "default")
    assert not block.enabled
    assert block.persona_id == "default"


def test_parse_agent_evaluator_on_profile_enabled() -> None:
    block = parse_agent_evaluator_workflow_block(ROOT, "agent_evaluator_on")
    assert block.enabled
    assert block.persona_id == "commerce"
    assert block.llm_evaluation_enabled is False
    assert block.auto_promote_probation is False
    assert block.auto_create_persona.enabled is False


def test_parse_agent_evaluator_llm_evaluation_enabled(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ae_llm.yaml").write_text(
        """version: 1
agent_evaluator:
  enabled: true
  persona_id: qa
  llm_evaluation_enabled: true
""",
        encoding="utf-8",
    )
    block = parse_agent_evaluator_workflow_block(tmp_path, "ae_llm")
    assert block.enabled
    assert block.llm_evaluation_enabled is True


def test_parse_agent_evaluator_missing_profile_returns_disabled() -> None:
    block = parse_agent_evaluator_workflow_block(ROOT, None)
    assert not block.enabled
    assert block.persona_id == "default"


def _write_agent_evaluator_profile(repo: Path, name: str, body: str) -> None:
    """Write ``configs/workflows/{name}.yaml`` under ``repo`` with the given body.

    Uses ``exist_ok=True`` so a single test can drop many per-case profiles into the
    same tmp directory; mirrors ``_write_self_refinement_profile`` from follow-on 53
    and the ``_write_profile`` helper in ``tests/test_workflow_security_metadata.py``.
    """
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_parse_agent_evaluator_malformed_block_yields_defaults(
    tmp_path: Path,
) -> None:
    """Pin §14 #15: scalar/list ``agent_evaluator:`` block → defaults.

    The ``if not isinstance(block, dict)`` early-return in
    :func:`parse_agent_evaluator_workflow_block` is the safety net for operator typos
    like ``agent_evaluator: true`` or ``agent_evaluator: []``. Lock both shapes so any
    refactor that wants to accept scalar shortcuts must update this test on purpose.
    Mirrors the malformed-block tests from follow-ons 52 / 53.
    """
    _write_agent_evaluator_profile(
        tmp_path,
        "block_scalar",
        "version: 1\nagent_evaluator: true\n",
    )
    _write_agent_evaluator_profile(
        tmp_path,
        "block_list",
        "version: 1\nagent_evaluator: []\n",
    )
    for name in ("block_scalar", "block_list"):
        block = parse_agent_evaluator_workflow_block(tmp_path, name)
        assert block == AgentEvaluatorWorkflowBlock(), name


def test_parse_agent_evaluator_field_coercion_contract(tmp_path: Path) -> None:
    """Pin ``enabled`` / ``persona_id`` coercion ladders (§14 #15).

    ``enabled`` is coerced via plain ``bool(...)`` — same surprising contract as
    self_refinement (follow-on 53): the quoted YAML string ``"false"`` resolves to
    ``enabled=True`` because ``bool("false")`` is truthy for non-empty strings.
    ``persona_id`` goes through ``str(persona_raw).strip()`` with a ``None``
    short-circuit and a post-strip empty fallback to ``"default"``, but a non-string
    YAML scalar like ``42`` is **kept** as the valid persona_id ``"42"`` because
    ``str(42).strip()`` is the truthy ``"42"`` rather than falling back to ``"default"``.
    Locks both contracts so any refactor (e.g. tightening ``persona_id`` to require
    ``isinstance(str)`` like self_refinement's ``description`` field) must update this
    test on purpose.
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
            "version: 1\nagent_evaluator:\n  persona_id: default\n"
            if name == "en_missing"
            else f"version: 1\nagent_evaluator:\n  enabled: {raw}\n"
        )
        _write_agent_evaluator_profile(tmp_path, name, body)
        block = parse_agent_evaluator_workflow_block(tmp_path, name)
        assert block.enabled is expected, name

    persona_cases: list[tuple[str, str, str]] = [
        ("p_padded", '"  commerce  "', "commerce"),
        ("p_null", "null", "default"),
        ("p_empty", '""', "default"),
        ("p_whitespace", '"   "', "default"),
        ("p_int_passthrough", "42", "42"),
        ("p_missing", "", "default"),
    ]
    for name, raw, expected in persona_cases:
        body = (
            "version: 1\nagent_evaluator:\n  enabled: true\n"
            if name == "p_missing"
            else f"version: 1\nagent_evaluator:\n  enabled: true\n  persona_id: {raw}\n"
        )
        _write_agent_evaluator_profile(tmp_path, name, body)
        block = parse_agent_evaluator_workflow_block(tmp_path, name)
        assert block.persona_id == expected, name


def test_agent_evaluator_enabled_bool_ladder_boundary_cases(tmp_path: Path) -> None:
    """Pin §14 #15 ``enabled`` ``bool()``-ladder boundary contract (parity twin of Part A).

    :func:`parse_agent_evaluator_workflow_block` coerces ``enabled`` via plain
    ``bool(block.get("enabled", False))`` — identical to
    :func:`parse_self_refinement_workflow_block` (follow-on 53). Follow-on 55
    pinned a single representative ``"false"`` divergence; this test locks the
    **full boundary surface** of the ``bool()`` ladder so any refactor must
    update both this and the parity twin in
    :func:`tests/test_workflow_self_refinement.py::test_self_refinement_enabled_bool_ladder_boundary_cases`
    (Part A of follow-on 60). The 12-case table is **identical** between the
    two parts; a refactor that flips one parser's coercion (e.g. switching only
    agent_evaluator to ``_coerce_yaml_bool``) must update both this test and
    its parity twin on purpose.

    All string variants are quoted to keep PyYAML's YAML 1.1 bool resolver from
    eagerly converting unquoted ``false`` / ``no`` / ``off`` to Python ``bool``
    and bypassing the ``bool(str)`` arm — same caveat documented in follow-on
    59 and Part A.
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
        _write_agent_evaluator_profile(
            repo,
            name,
            f"version: 1\nagent_evaluator:\n  enabled: {raw}\n",
        )
        block = parse_agent_evaluator_workflow_block(repo, name)
        assert block.enabled is expected, f"enabled={raw}"
