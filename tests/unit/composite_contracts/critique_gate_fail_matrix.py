from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from agent_core.models import EventType, FindingCreatedPayload
from env import find_repo_root
from orchestrator.llm import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow.universal_critique import effective_universal_critique
from unit.composite_contract_fixtures import (
    FINDING_CREATED,
    append_fail_gate,
    emit_critique_gate_fail_findings,
    findings_for_run,
    stage_names_from_findings,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[2])

ENV_ALL_ON = {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"}
ENV_IMPL_ONLY = {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"}

UC_EXPECTED_STAGES = [
    IMPLEMENTATION_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
]

CANONICAL_STAGE_ORDER = (
    IMPLEMENTATION_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
)

REVERSE_STAGE_ORDER = (
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
)


def _critique_finding_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r.get("event_type") == FINDING_CREATED
        and (r.get("metadata") or {}).get("critique_gate_fail_finding") is True
    ]


def _append_gates(mem: Any, run_id: Any, stages: tuple[str, ...]) -> None:
    for stage in stages:
        append_fail_gate(mem, run_id, stage)


def _validate_eff_none_fallback_param(case: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    assert len(findings) == case["expected_len"], case["case_id"]
    if case["expect_stages"]:
        assert stage_names_from_findings(findings) == UC_EXPECTED_STAGES, case["case_id"]


def _validate_b1_order(_case: dict[str, Any], stage_names: list[str | None]) -> None:
    assert stage_names == list(UC_EXPECTED_STAGES)


def _validate_b2_idempotence(_case: dict[str, Any], counts: tuple[int, int]) -> None:
    first_count, second_count = counts
    assert first_count == 3 and second_count == 3


def _validate_b3_triple(_case: dict[str, Any], count: int) -> None:
    assert count == 3


def _validate_b4_between_calls(_case: dict[str, Any], count: int) -> None:
    assert count == 3


def _validate_b5_explicit_order(_case: dict[str, Any], stage_names: list[str | None]) -> None:
    assert stage_names == list(UC_EXPECTED_STAGES)


def _validate_c1_ctx_once(_case: dict[str, Any], call_count: int) -> None:
    assert call_count == 1


def _validate_c4_context_kwarg(_case: dict[str, Any], captured: list[dict[str, Any]]) -> None:
    assert len(captured) == 3
    for idx, call_kwargs in enumerate(captured):
        assert "context" in call_kwargs, f"C4: model_validate call #{idx} must use context= kwarg"


def _validate_c5_context_identity(_case: dict[str, Any], captured: list[Any]) -> None:
    assert len(captured) == 3
    assert id(captured[0]) == id(captured[1]) == id(captured[2])


def _validate_d1_list_calls(_case: dict[str, Any], call_count: int) -> None:
    assert call_count == 4


def _validate_d2_list_calls(_case: dict[str, Any], call_count: int) -> None:
    assert call_count == 1


def _validate_d3_list_calls(_case: dict[str, Any], call_count: int) -> None:
    assert call_count == 2


def _validate_d4_already_emitted(_case: dict[str, Any], spy: Any) -> None:
    assert spy.call_count == 5
    impl_call_rows = spy.call_args_list[0].args[0]
    tw_call_rows = spy.call_args_list[1].args[0]
    planner_call_rows = spy.call_args_list[2].args[0]
    assert len(_critique_finding_rows(impl_call_rows)) == 0
    assert len(_critique_finding_rows(tw_call_rows)) == 1
    assert len(_critique_finding_rows(planner_call_rows)) == 2


def _validate_d5_refresh_order(_case: dict[str, Any], next_call: str) -> None:
    assert next_call == "list_run_events"


EFF_NONE_FALLBACK_PARAM_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a1",
        "env_patch": None,
        "expected_len": 0,
        "expect_stages": False,
        "validate": _validate_eff_none_fallback_param,
    },
    {
        "case_id": "a2",
        "env_patch": ENV_IMPL_ONLY,
        "expected_len": 3,
        "expect_stages": True,
        "validate": _validate_eff_none_fallback_param,
    },
    {
        "case_id": "a3",
        "env_patch": ENV_ALL_ON,
        "expected_len": 3,
        "expect_stages": False,
        "validate": _validate_eff_none_fallback_param,
    },
)

ITERATION_ORDER_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1",
        "gate_order": REVERSE_STAGE_ORDER,
        "validate": _validate_b1_order,
    },
    {
        "case_id": "b2",
        "gate_order": CANONICAL_STAGE_ORDER,
        "emit_calls": 2,
        "validate": _validate_b2_idempotence,
    },
    {
        "case_id": "b3",
        "gate_order": CANONICAL_STAGE_ORDER,
        "emit_calls": 3,
        "validate": _validate_b3_triple,
    },
    {
        "case_id": "b4",
        "gate_order": CANONICAL_STAGE_ORDER,
        "between_calls_gate": IMPLEMENTATION_CRITIQUE_STAGE,
        "validate": _validate_b4_between_calls,
    },
    {
        "case_id": "b5",
        "gate_order": REVERSE_STAGE_ORDER,
        "explicit_eff": True,
        "validate": _validate_b5_explicit_order,
    },
)

STRICTNESS_CONTEXT_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1",
        "gate_order": CANONICAL_STAGE_ORDER,
        "validate": _validate_c1_ctx_once,
    },
    {
        "case_id": "c2",
        "gate_order": (IMPLEMENTATION_CRITIQUE_STAGE,),
        "validate": _validate_c1_ctx_once,
    },
    {
        "case_id": "c3",
        "gate_order": (),
        "validate": _validate_c1_ctx_once,
    },
    {
        "case_id": "c4",
        "gate_order": CANONICAL_STAGE_ORDER,
        "spy_model_validate": "kwargs",
        "validate": _validate_c4_context_kwarg,
    },
    {
        "case_id": "c5",
        "gate_order": CANONICAL_STAGE_ORDER,
        "spy_model_validate": "context",
        "validate": _validate_c5_context_identity,
    },
)

ROWS_REFRESH_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "d1",
        "gate_order": CANONICAL_STAGE_ORDER,
        "validate": _validate_d1_list_calls,
    },
    {
        "case_id": "d2",
        "gate_order": (),
        "validate": _validate_d2_list_calls,
    },
    {
        "case_id": "d3",
        "gate_order": (IMPLEMENTATION_CRITIQUE_STAGE,),
        "validate": _validate_d3_list_calls,
    },
    {
        "case_id": "d4",
        "gate_order": CANONICAL_STAGE_ORDER,
        "spy_already_emitted": True,
        "validate": _validate_d4_already_emitted,
    },
    {
        "case_id": "d5",
        "gate_order": (IMPLEMENTATION_CRITIQUE_STAGE,),
        "spy_append_order": True,
        "validate": _validate_d5_refresh_order,
    },
)


def run_eff_none_fallback_param(case: dict[str, Any]) -> list[dict[str, Any]]:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    return emit_critique_gate_fail_findings(orch, mem, rid, env=case["env_patch"])


def run_eff_none_fallback_parity() -> None:
    orch_none, mem_none = make_dev_orchestrator()
    rid_none = orch_none.create_run("default")
    orch_expl, mem_expl = make_dev_orchestrator()
    rid_expl = orch_expl.create_run("default")
    _append_gates(mem_none, rid_none, CANONICAL_STAGE_ORDER)
    _append_gates(mem_expl, rid_expl, CANONICAL_STAGE_ORDER)
    with patch.dict(os.environ, ENV_ALL_ON, clear=False):
        orch_none._maybe_emit_critique_gate_fail_findings(rid_none)  # noqa: SLF001
        eff_explicit = effective_universal_critique(ROOT, "default")
        orch_expl._maybe_emit_critique_gate_fail_findings(rid_expl, eff_explicit)  # noqa: SLF001
    assert stage_names_from_findings(findings_for_run(mem_none, rid_none)) == stage_names_from_findings(
        findings_for_run(mem_expl, rid_expl)
    )


def run_eff_none_fallback_resolver() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_gates(mem, rid, CANONICAL_STAGE_ORDER)
    with (
        patch.dict(os.environ, ENV_ALL_ON, clear=False),
        patch.object(
            orch,
            "_effective_universal_critique_for_run",
            wraps=orch._effective_universal_critique_for_run,  # noqa: SLF001
        ) as resolver_spy,
    ):
        orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
    assert resolver_spy.call_count == 1


def run_iteration_order_case(case: dict[str, Any]) -> Any:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_gates(mem, rid, case["gate_order"])
    with patch.dict(os.environ, ENV_ALL_ON, clear=False):
        if case.get("explicit_eff"):
            eff = effective_universal_critique(ROOT, "default")
            orch._maybe_emit_critique_gate_fail_findings(rid, eff)  # noqa: SLF001
            return stage_names_from_findings(findings_for_run(mem, rid))
        emit_calls = case.get("emit_calls", 1)
        if case.get("between_calls_gate"):
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
            append_fail_gate(mem, rid, case["between_calls_gate"])
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
            return len(findings_for_run(mem, rid))
        if emit_calls == 1:
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
            return stage_names_from_findings(findings_for_run(mem, rid))
        if emit_calls == 2:
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
            first_count = len(findings_for_run(mem, rid))
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
            second_count = len(findings_for_run(mem, rid))
            return first_count, second_count
        for _ in range(emit_calls):
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
        return len(findings_for_run(mem, rid))
    raise AssertionError(f"unhandled iteration case: {case['case_id']!r}")


def run_strictness_context_case(case: dict[str, Any]) -> Any:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_gates(mem, rid, case["gate_order"])
    original_validate = FindingCreatedPayload.model_validate
    spy_mode = case.get("spy_model_validate")
    captured: list[Any] = []

    def spy_validate(*args: Any, **kwargs: Any) -> Any:
        if spy_mode == "kwargs":
            captured.append(dict(kwargs))
        elif spy_mode == "context":
            captured.append(kwargs.get("context"))
        return original_validate(*args, **kwargs)

    patches: list[Any] = [
        patch.dict(os.environ, ENV_ALL_ON, clear=False),
        patch.object(orch, "_strictness_context", wraps=orch._strictness_context),  # noqa: SLF001
    ]
    if spy_mode:
        patches.append(patch.object(FindingCreatedPayload, "model_validate", spy_validate))

    with ExitStack() as stack:
        ctx_spy = stack.enter_context(patches[1])
        stack.enter_context(patches[0])
        if spy_mode:
            stack.enter_context(patches[2])
        orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001

    if spy_mode:
        return captured
    return ctx_spy.call_count


def run_rows_refresh_case(case: dict[str, Any]) -> Any:
    with patch.dict(os.environ, ENV_ALL_ON, clear=False):
        eff_all_on = effective_universal_critique(ROOT, "default")

    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_gates(mem, rid, case["gate_order"])

    if case.get("spy_already_emitted"):
        with (
            patch.dict(os.environ, ENV_ALL_ON, clear=False),
            patch.object(
                orch,
                "_critique_gate_fail_finding_already_emitted",
                wraps=orch._critique_gate_fail_finding_already_emitted,  # noqa: SLF001
            ) as already_spy,
        ):
            orch._maybe_emit_critique_gate_fail_findings(rid)  # noqa: SLF001
        return already_spy

    if case.get("spy_append_order"):
        parent = MagicMock()
        with (
            patch.object(orch, "_strictness_context", return_value={}),
            patch.object(
                orch._store,  # noqa: SLF001
                "append",
                wraps=orch._store.append,  # noqa: SLF001
            ) as append_spy,
            patch.object(
                orch._store,  # noqa: SLF001
                "list_run_events",
                wraps=orch._store.list_run_events,  # noqa: SLF001
            ) as list_spy,
        ):
            parent.attach_mock(append_spy, "append")
            parent.attach_mock(list_spy, "list_run_events")
            orch._maybe_emit_critique_gate_fail_findings(rid, eff_all_on)  # noqa: SLF001
        finding_appends = [
            c
            for c in parent.mock_calls
            if c[0] == "append"
            and len(c.args) >= 1
            and getattr(c.args[0], "event_type", None) == EventType.FINDING_CREATED
        ]
        assert len(finding_appends) == 1
        finding_append_idx = parent.mock_calls.index(finding_appends[0])
        method_names_after = [c[0] for c in parent.mock_calls[finding_append_idx + 1 :]]
        assert method_names_after
        return method_names_after[0]

    with (
        patch.object(orch, "_strictness_context", return_value={}),
        patch.object(
            orch._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch._store.list_run_events,  # noqa: SLF001
        ) as list_spy,
    ):
        orch._maybe_emit_critique_gate_fail_findings(rid, eff_all_on)  # noqa: SLF001
    return list_spy.call_count
