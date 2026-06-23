from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from agent_core.models import (
    EventType,
    FindingCreatedPayload,
)
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.llm_plan import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
)

if TYPE_CHECKING:
    pass

from unit.composite_contract_fixtures import (
    FINDING_CREATED,
    append_fail_gate,
    findings_for_run,
    stage_names_from_findings,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])

_ENV_ALL_ON = {
    "NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1",
}

_ENV_IMPL_ONLY = {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"}


def test_critique_gate_fail_findings_eff_none_fallback_5_axis() -> None:
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    append_fail_gate(mem_a1, rid_a1, IMPLEMENTATION_CRITIQUE_STAGE)
    append_fail_gate(mem_a1, rid_a1, TEST_WRITER_CRITIQUE_STAGE)
    append_fail_gate(mem_a1, rid_a1, PLANNER_CRITIQUE_STAGE)
    orch_a1._maybe_emit_critique_gate_fail_findings(rid_a1)  # noqa: SLF001
    assert findings_for_run(mem_a1, rid_a1) == [], (
        "A1: eff=None + default workflow + no env -> fallback resolves to "
        "no-emit eff (all 3 emit_finding_on_gate_fail flags False) -> "
        "0 findings even with 3 FAIL gates present"
    )

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    append_fail_gate(mem_a2, rid_a2, IMPLEMENTATION_CRITIQUE_STAGE)
    append_fail_gate(mem_a2, rid_a2, TEST_WRITER_CRITIQUE_STAGE)
    append_fail_gate(mem_a2, rid_a2, PLANNER_CRITIQUE_STAGE)
    with patch.dict(os.environ, _ENV_IMPL_ONLY, clear=False):
        orch_a2._maybe_emit_critique_gate_fail_findings(rid_a2)  # noqa: SLF001
    findings_a2 = findings_for_run(mem_a2, rid_a2)
    assert stage_names_from_findings(findings_a2) == [
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ], "A2: eff=None + global emit env on -> 3 findings; global UC env applies all panels"

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    append_fail_gate(mem_a3, rid_a3, IMPLEMENTATION_CRITIQUE_STAGE)
    append_fail_gate(mem_a3, rid_a3, TEST_WRITER_CRITIQUE_STAGE)
    append_fail_gate(mem_a3, rid_a3, PLANNER_CRITIQUE_STAGE)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_a3._maybe_emit_critique_gate_fail_findings(rid_a3)  # noqa: SLF001
    findings_a3 = findings_for_run(mem_a3, rid_a3)
    assert len(findings_a3) == 3, "A3: eff=None + all 3 envs on -> 3 findings"

    orch_a4_none, mem_a4_none = make_dev_orchestrator()
    rid_a4_none = orch_a4_none.create_run("default")
    orch_a4_expl, mem_a4_expl = make_dev_orchestrator()
    rid_a4_expl = orch_a4_expl.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_a4_none, rid_a4_none, stage)
        append_fail_gate(mem_a4_expl, rid_a4_expl, stage)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_a4_none._maybe_emit_critique_gate_fail_findings(rid_a4_none)  # noqa: SLF001
        eff_explicit = effective_universal_critique(ROOT, "default")
        orch_a4_expl._maybe_emit_critique_gate_fail_findings(  # noqa: SLF001
            rid_a4_expl,
            eff_explicit,
        )
    assert stage_names_from_findings(findings_for_run(mem_a4_none, rid_a4_none)) == stage_names_from_findings(
        findings_for_run(mem_a4_expl, rid_a4_expl),
    ), (
        "A4: eff=None fallback path yields IDENTICAL stage_name order as "
        "explicit-eff path (parity confirmation); pins fallback is "
        "semantically equivalent to the public effective_universal_critique call"
    )

    orch_a5, mem_a5 = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_a5, rid_a5, stage)
    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(
            orch_a5,
            "_effective_universal_critique_for_run",
            wraps=orch_a5._effective_universal_critique_for_run,  # noqa: SLF001
        ) as resolver_spy,
    ):
        orch_a5._maybe_emit_critique_gate_fail_findings(rid_a5)  # noqa: SLF001
    assert resolver_spy.call_count == 1, (
        "A5: fallback resolver _effective_universal_critique_for_run called "
        "EXACTLY ONCE per _maybe_emit_* call (regardless of 3 emissions); "
        "pins resolver is NOT re-invoked per-stage iteration"
    )


def test_critique_gate_fail_findings_iteration_order_and_idempotence_5_axis() -> None:
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    append_fail_gate(mem_b1, rid_b1, PLANNER_CRITIQUE_STAGE)
    append_fail_gate(mem_b1, rid_b1, TEST_WRITER_CRITIQUE_STAGE)
    append_fail_gate(mem_b1, rid_b1, IMPLEMENTATION_CRITIQUE_STAGE)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_b1._maybe_emit_critique_gate_fail_findings(rid_b1)  # noqa: SLF001
    assert stage_names_from_findings(findings_for_run(mem_b1, rid_b1)) == [
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ], (
        "B1: emitted findings are in strict list order [impl, tw, planner] "
        "EVEN WHEN gates were appended in reverse order; pins the literal "
        "loop order at pipeline.py:913-917 is independent of gate-append order"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_b2, rid_b2, stage)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_b2._maybe_emit_critique_gate_fail_findings(rid_b2)  # noqa: SLF001
        first_count = len(findings_for_run(mem_b2, rid_b2))
        orch_b2._maybe_emit_critique_gate_fail_findings(rid_b2)  # noqa: SLF001
        second_count = len(findings_for_run(mem_b2, rid_b2))
    assert first_count == 3 and second_count == 3, (
        f"B2: double-call idempotence -- first call 3 findings, second still 3 "
        f"(got first={first_count}, second={second_count}); pins per-stage "
        "dedup blocks the same call from re-emitting on a repeat invocation"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_b3, rid_b3, stage)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        for _ in range(3):
            orch_b3._maybe_emit_critique_gate_fail_findings(rid_b3)  # noqa: SLF001
    assert len(findings_for_run(mem_b3, rid_b3)) == 3, (
        "B3: triple-call -- third call STILL emits 0; pins idempotence holds "
        "beyond one repeat (no edge-case slip after multiple retries)"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_b4, rid_b4, stage)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_b4._maybe_emit_critique_gate_fail_findings(rid_b4)  # noqa: SLF001
        append_fail_gate(mem_b4, rid_b4, IMPLEMENTATION_CRITIQUE_STAGE)
        orch_b4._maybe_emit_critique_gate_fail_findings(rid_b4)  # noqa: SLF001
    assert len(findings_for_run(mem_b4, rid_b4)) == 3, (
        "B4: a new FAIL gate for impl appended BETWEEN calls does NOT cause "
        "a second impl finding; pins per-stage dedup is 'any prior finding "
        "for stage' (metadata.stage_name match), NOT 'matched against the "
        "latest gate row'"
    )

    orch_b5, mem_b5 = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    append_fail_gate(mem_b5, rid_b5, PLANNER_CRITIQUE_STAGE)
    append_fail_gate(mem_b5, rid_b5, TEST_WRITER_CRITIQUE_STAGE)
    append_fail_gate(mem_b5, rid_b5, IMPLEMENTATION_CRITIQUE_STAGE)
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        eff_b5 = effective_universal_critique(ROOT, "default")
        orch_b5._maybe_emit_critique_gate_fail_findings(rid_b5, eff_b5)  # noqa: SLF001
    assert stage_names_from_findings(findings_for_run(mem_b5, rid_b5)) == [
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ], (
        "B5: explicit-eff path yields the SAME ordering as B1's None-fallback "
        "path; pins fo103's order invariant is path-independent"
    )


def test_critique_gate_fail_findings_strictness_context_propagation_5_axis() -> None:
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_c1, rid_c1, stage)
    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(
            orch_c1,
            "_strictness_context",
            wraps=orch_c1._strictness_context,  # noqa: SLF001
        ) as ctx_spy_c1,
    ):
        orch_c1._maybe_emit_critique_gate_fail_findings(rid_c1)  # noqa: SLF001
    assert ctx_spy_c1.call_count == 1, (
        "C1: _strictness_context called EXACTLY ONCE across 3 emissions; "
        "pins ctx is NOT re-fetched per stage iteration (called outside the "
        "loop at pipeline.py:919)"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    append_fail_gate(mem_c2, rid_c2, IMPLEMENTATION_CRITIQUE_STAGE)
    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(
            orch_c2,
            "_strictness_context",
            wraps=orch_c2._strictness_context,  # noqa: SLF001
        ) as ctx_spy_c2,
    ):
        orch_c2._maybe_emit_critique_gate_fail_findings(rid_c2)  # noqa: SLF001
    assert ctx_spy_c2.call_count == 1, (
        "C2: _strictness_context called EXACTLY ONCE across 1 emission "
        "(impl-only gate); pins call-count invariant holds regardless of "
        "emission count"
    )

    orch_c3, _ = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(
            orch_c3,
            "_strictness_context",
            wraps=orch_c3._strictness_context,  # noqa: SLF001
        ) as ctx_spy_c3,
    ):
        orch_c3._maybe_emit_critique_gate_fail_findings(rid_c3)  # noqa: SLF001
    assert ctx_spy_c3.call_count == 1, (
        "C3: _strictness_context STILL called once on zero-emit call (env on "
        "but no gates -> all 3 skip via no-gate arm); pins ctx fetch is "
        "UNCONDITIONAL before the loop (not gated on emission count)"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_c4, rid_c4, stage)
    original_validate = FindingCreatedPayload.model_validate
    captured_c4: list[dict[str, Any]] = []

    def spy_validate_c4(*args: Any, **kwargs: Any) -> Any:
        captured_c4.append(dict(kwargs))
        return original_validate(*args, **kwargs)

    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(FindingCreatedPayload, "model_validate", spy_validate_c4),
    ):
        orch_c4._maybe_emit_critique_gate_fail_findings(rid_c4)  # noqa: SLF001
    assert len(captured_c4) == 3, "C4: model_validate called 3 times (one per emit)"
    for idx, call_kwargs in enumerate(captured_c4):
        assert "context" in call_kwargs, (
            f"C4: model_validate call #{idx} threads ctx via `context=` KWARG, "
            "not positionally; pins keyword routing (would silently break if "
            "the helper were refactored to positional argument)"
        )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_c5, rid_c5, stage)
    captured_c5: list[Any] = []

    def spy_validate_c5(*args: Any, **kwargs: Any) -> Any:
        captured_c5.append(kwargs.get("context"))
        return original_validate(*args, **kwargs)

    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(FindingCreatedPayload, "model_validate", spy_validate_c5),
    ):
        orch_c5._maybe_emit_critique_gate_fail_findings(rid_c5)  # noqa: SLF001
    assert len(captured_c5) == 3, "C5: 3 context captures"
    assert id(captured_c5[0]) == id(captured_c5[1]) == id(captured_c5[2]), (
        "C5: the SAME ctx dict instance is passed to all 3 model_validate calls "
        "(id() identity); pins ctx is fetched once into a local variable and "
        "reused across iterations -- proves no per-iteration re-fetch (which "
        "would produce 3 distinct {} dicts under default policy)"
    )


def test_critique_gate_fail_findings_rows_refresh_invariant_5_axis() -> None:
    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        eff_all_on = effective_universal_critique(ROOT, "default")

    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_d1, rid_d1, stage)
    with (
        patch.object(orch_d1, "_strictness_context", return_value={}),
        patch.object(
            orch_d1._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch_d1._store.list_run_events,  # noqa: SLF001
        ) as list_spy_d1,
    ):
        orch_d1._maybe_emit_critique_gate_fail_findings(rid_d1, eff_all_on)  # noqa: SLF001
    assert list_spy_d1.call_count == 4, (
        f"D1: 3-emit call -> list_run_events called 4 times (1 initial at "
        f"pipeline.py:918 + 1 refresh per emit at pipeline.py:958 x3 emits); "
        f"got {list_spy_d1.call_count}. Pins refresh fires exactly once per "
        "successful emission"
    )

    orch_d2, _ = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    with (
        patch.object(orch_d2, "_strictness_context", return_value={}),
        patch.object(
            orch_d2._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch_d2._store.list_run_events,  # noqa: SLF001
        ) as list_spy_d2,
    ):
        orch_d2._maybe_emit_critique_gate_fail_findings(rid_d2, eff_all_on)  # noqa: SLF001
    assert list_spy_d2.call_count == 1, (
        f"D2: zero-emit call (env on, no gates) -> list_run_events called "
        f"EXACTLY ONCE (initial scan only); got {list_spy_d2.call_count}. "
        "Pins refresh is NOT triggered on skip paths (only after a successful "
        "append at pipeline.py:945-957)"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    append_fail_gate(mem_d3, rid_d3, IMPLEMENTATION_CRITIQUE_STAGE)
    with (
        patch.object(orch_d3, "_strictness_context", return_value={}),
        patch.object(
            orch_d3._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch_d3._store.list_run_events,  # noqa: SLF001
        ) as list_spy_d3,
    ):
        orch_d3._maybe_emit_critique_gate_fail_findings(rid_d3, eff_all_on)  # noqa: SLF001
    assert list_spy_d3.call_count == 2, (
        f"D3: 1-emit call (impl-only gate) -> list_run_events called 2 times "
        f"(1 initial + 1 refresh after impl emit); got {list_spy_d3.call_count}. "
        "Pins refresh is per-emit, NOT per-iteration (tw and planner iterations "
        "skip via no-gate arm and do NOT trigger refresh)"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem_d4, rid_d4, stage)
    with (
        patch.dict(os.environ, _ENV_ALL_ON, clear=False),
        patch.object(
            orch_d4,
            "_critique_gate_fail_finding_already_emitted",
            wraps=orch_d4._critique_gate_fail_finding_already_emitted,  # noqa: SLF001
        ) as already_spy_d4,
    ):
        orch_d4._maybe_emit_critique_gate_fail_findings(rid_d4)  # noqa: SLF001

    assert already_spy_d4.call_count == 5, "D4 setup: spy called once per enabled stage iter"

    def _critique_finding_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            r
            for r in rows
            if r.get("event_type") == FINDING_CREATED
            and (r.get("metadata") or {}).get("critique_gate_fail_finding") is True
        ]

    impl_call_rows = already_spy_d4.call_args_list[0].args[0]
    tw_call_rows = already_spy_d4.call_args_list[1].args[0]
    planner_call_rows = already_spy_d4.call_args_list[2].args[0]
    assert len(_critique_finding_rows(impl_call_rows)) == 0, (
        "D4: impl iteration sees ZERO prior critique-gate-fail findings "
        "(initial rows snapshot before any emission)"
    )
    assert len(_critique_finding_rows(tw_call_rows)) == 1, (
        "D4: tw iteration sees EXACTLY ONE prior critique-gate-fail finding "
        "(the impl finding just emitted); pins the in-loop refresh at "
        "pipeline.py:958 makes new findings visible to subsequent iterations "
        "within the same call"
    )
    assert len(_critique_finding_rows(planner_call_rows)) == 2, (
        "D4 cross-cut: planner iteration sees TWO prior critique-gate-fail "
        "findings (impl + tw); pins refresh accumulates across iterations"
    )

    orch_d5, mem_d5 = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    append_fail_gate(mem_d5, rid_d5, IMPLEMENTATION_CRITIQUE_STAGE)
    parent = MagicMock()
    with (
        patch.object(orch_d5, "_strictness_context", return_value={}),
        patch.object(
            orch_d5._store,  # noqa: SLF001
            "append",
            wraps=orch_d5._store.append,  # noqa: SLF001
        ) as append_spy_d5,
        patch.object(
            orch_d5._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch_d5._store.list_run_events,  # noqa: SLF001
        ) as list_spy_d5,
    ):
        parent.attach_mock(append_spy_d5, "append")
        parent.attach_mock(list_spy_d5, "list_run_events")
        orch_d5._maybe_emit_critique_gate_fail_findings(rid_d5, eff_all_on)  # noqa: SLF001

    method_names = [c[0] for c in parent.mock_calls]
    finding_appends = [
        c
        for c in parent.mock_calls
        if c[0] == "append"
        and len(c.args) >= 1
        and getattr(c.args[0], "event_type", None) == EventType.FINDING_CREATED
    ]
    assert len(finding_appends) == 1, (
        f"D5 setup: exactly one FINDING_CREATED append; got {len(finding_appends)}"
    )
    finding_append_idx = parent.mock_calls.index(finding_appends[0])
    method_names_after = method_names[finding_append_idx + 1 :]
    assert method_names_after, (
        "D5 setup: FINDING_CREATED append must be followed by at least one mock call"
    )
    assert method_names_after[0] == "list_run_events", (
        f"D5: the call IMMEDIATELY AFTER the FINDING_CREATED append must be a "
        f"list_run_events refresh; got next call '{method_names_after[0]}'. Pins "
        "refresh-AFTER-append ordering at pipeline.py:945-958 (would break "
        "silently if refactored to refresh-BEFORE-append, which could cause "
        "subsequent iterations to miss the just-emitted finding)"
    )
