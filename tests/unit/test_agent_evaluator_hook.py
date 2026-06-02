"""Agent evaluator stage marker (env or workflow YAML)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from agent_core.models import EventType
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorAutoCreatePersonaBlock,
    AgentEvaluatorWorkflowBlock,
)


def _has_agent_eval_stage(events: list[dict[str, Any]]) -> bool:
    """Return True iff ``events`` contains a ``stage.started`` row whose payload
    ``stage_name`` begins with ``agent_eval:``.

    Factors out the recurring assertion used by the follow-on 63 string-arm
    contract tests below. The three pre-existing tests above keep their inline
    assertion to avoid mixing a behavioral slice with refactor noise outside
    follow-on 63's scope.
    """
    return any(
        r["event_type"] == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
        for r in events
    )


def test_agent_evaluator_emits_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    assert any(
        r["event_type"] == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
        for r in evs
    )


def test_agent_evaluator_llm_policy_branch_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "1")
    monkeypatch.setenv("HERMES_USE_LLM", "1")
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR_LLM_STUB", "1")
    block = AgentEvaluatorWorkflowBlock(
        enabled=True,
        persona_id="commerce",
        llm_evaluation_enabled=True,
        auto_create_persona=AgentEvaluatorAutoCreatePersonaBlock(),
    )
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.parse_agent_evaluator_workflow_block",
            return_value=block,
        ),
        patch.object(orch, "_selected_model_for_run", return_value="stub-model"),
        patch(
            "hermes_orchestrator.pipeline.execute_agent_evaluator_policy_llm",
            return_value=None,
        ),
    ):
        orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    stage = next(
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
    )
    ae = (stage.get("metadata") or {}).get("agent_evaluator") or {}
    assert ae.get("evaluation_branch") == "rules_with_llm_policy"
    llm_eval = ae.get("llm_evaluation")
    assert isinstance(llm_eval, dict)
    assert ae.get("evaluation", {}).get("status") is not None
    rules_eval = ae.get("evaluation") or {}
    if isinstance(rules_eval.get("score"), (int, float)):
        assert llm_eval.get("policy_score") == float(rules_eval["score"])
        assert llm_eval.get("policy_score_band") in (
            "below_threshold",
            "meets_threshold",
            "strong",
        )


def test_agent_eval_yaml_emits_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERMES_AGENT_EVALUATOR", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_on")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    assert any(
        r["event_type"] == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "agent_eval:commerce"
        for r in evs
    )


def test_agent_eval_env_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "0")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_on")
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    assert not any(
        r["event_type"] == EventType.STAGE_STARTED.value
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
        for r in evs
    )


def test_agent_evaluator_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #15 env force-on tuple ``.strip().lower() in ("1", "true", "yes")``.

    :meth:`RunOrchestrator._maybe_emit_agent_evaluator_stage` consults
    ``HERMES_AGENT_EVALUATOR`` *before* the workflow YAML check. Existing
    tests sample only `"1"`; this test exhaustively pins the case-folded +
    whitespace-trimmed variants of the force-on tuple. The workflow profile is
    ``default`` (``agent_evaluator.enabled: false`` in
    [`configs/workflows/default.yaml`](d:\\Hermes\\configs\\workflows\\default.yaml))
    so any emitted ``stage.started`` ``agent_eval:*`` event comes only from the
    env force-on branch.

    Parallel to follow-on 62 Part A (security-metadata env layer) and
    follow-on 51's :func:`env_over_yaml` asymmetry slice. Per-case
    ``force_on raw=<raw>`` message identifies the failing env scalar.
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
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("ws_upper_true_pad", "  TRUE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("HERMES_AGENT_EVALUATOR", raw)
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
        assert _has_agent_eval_stage(mem.list_run_events(str(rid))), f"force_on raw={raw!r}"


def test_agent_evaluator_env_kill_switch_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #15 env kill-switch tuple ``.strip().lower() in ("0", "false", "no")``.

    Mirror of Part A for the falsy tuple. The workflow profile is
    ``agent_evaluator_on`` (``agent_evaluator.enabled: true``) so any
    **absence** of the ``stage.started`` event comes only from the env
    kill-switch branch. Existing coverage samples only `"0"`; this test pins
    the full case-folded + whitespace-trimmed variants. Per-case
    ``kill_switch raw=<raw>`` message identifies the failing env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_zero", "0"),
        ("canon_false", "false"),
        ("canon_no", "no"),
        ("upper_false", "FALSE"),
        ("title_false", "False"),
        ("upper_no", "NO"),
        ("title_no", "No"),
        ("mixed_false", "fAlSe"),
        ("mixed_no", "nO"),
        ("ws_zero_pad", "  0  "),
        ("ws_false_pad", " false "),
        ("ws_tab_no_lf", "\tno\n"),
        ("ws_upper_false_pad", "  FALSE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("HERMES_AGENT_EVALUATOR", raw)
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("agent_evaluator_on")
        orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
        assert not _has_agent_eval_stage(mem.list_run_events(str(rid))), f"kill_switch raw={raw!r}"


def test_agent_evaluator_env_fallthrough_to_yaml_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #15 exclusive-tuple-membership: env values not in either tuple fall through to YAML.

    Critical asymmetry pinned: the underlying YAML coercion in
    :func:`parse_agent_evaluator_workflow_block` ultimately reads
    ``block.enabled`` (plain ``bool(...)``-ladder for the agent-evaluator
    parser, see follow-on 60 Part B), but the env layer's tuples in
    :meth:`_maybe_emit_agent_evaluator_stage` are ``("1", "true", "yes")``
    and ``("0", "false", "no")`` — they **exclude** ``"on"`` / ``"off"``. So
    ``HERMES_AGENT_EVALUATOR=on`` falls past both tuples to the workflow YAML
    check rather than forcing-on. Parallel to follow-on 51 (:func:`env_over_yaml`
    asymmetry) and follow-on 62 (security-metadata env layer).

    Each case asserts against **both** repo profiles (``default`` → no emit,
    ``agent_evaluator_on`` → emit) so the asymmetry surfaces with a single
    per-case message identifying both the failing workflow side and the
    offending env scalar. Covers four fallthrough failure modes:

    1. **Asymmetric YAML tokens** (``"on"`` / ``"off"`` / ``"ON"`` / ``"  OFF  "``).
    2. **Stripped-to-empty inputs** (``""`` / ``"   "``).
    3. **Unknown tokens** (``"maybe"`` / ``"true!"``).
    4. **Interior whitespace** (``" ye s "``).

    A future "unify the env tuple with the workflow coercion tuple" refactor
    (adding ``"on"`` / ``"off"`` to the env tuples) would silently flip the
    semantics of ``HERMES_AGENT_EVALUATOR=on`` from "follow YAML" to "force
    on" — this test fails loudly on exactly that change.
    """
    cases: list[tuple[str, str]] = [
        ("fall_on", "on"),
        ("fall_off", "off"),
        ("fall_upper_on", "ON"),
        ("fall_padded_off", "  OFF  "),
        ("fall_empty", ""),
        ("fall_whitespace", "   "),
        ("fall_maybe", "maybe"),
        ("fall_near_miss", "true!"),
        ("fall_interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("HERMES_AGENT_EVALUATOR", raw)
        orch_off, mem_off = make_dev_orchestrator()
        rid_off = orch_off.create_run("default")
        orch_off._maybe_emit_agent_evaluator_stage(rid_off)  # noqa: SLF001
        assert not _has_agent_eval_stage(mem_off.list_run_events(str(rid_off))), (
            f"fall_through workflow=off raw={raw!r}"
        )
        orch_on, mem_on = make_dev_orchestrator()
        rid_on = orch_on.create_run("agent_evaluator_on")
        orch_on._maybe_emit_agent_evaluator_stage(rid_on)  # noqa: SLF001
        assert _has_agent_eval_stage(mem_on.list_run_events(str(rid_on))), (
            f"fall_through workflow=on raw={raw!r}"
        )
