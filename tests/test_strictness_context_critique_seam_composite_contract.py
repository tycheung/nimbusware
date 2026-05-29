"""Per-run resolver composite for strictness + universal critique.

Two sibling private methods of ``RunOrchestrator`` in
[packages/hermes_orchestrator/pipeline.py](packages/hermes_orchestrator/pipeline.py):

.. code-block:: python

 def _strictness_context(self, run_id: UUID) -> dict[str, Any]: # 554-559
 snap = self.policy_snapshot_for_run(run_id)
 fs = snap.get("finding_fix_strictness")
 if isinstance(fs, dict):
 return {"finding_fix_strictness": FindingFixStrictnessSettings.model_validate(fs)}
 return {}

 def _effective_universal_critique_for_run( # 700-702
 self, run_id: UUID,
 ) -> EffectiveUniversalCritique:
 wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
 return effective_universal_critique(self._repo_root, wf)

Both helpers consume the **same** row source
(``self._store.list_run_events(str(run_id))``) but **different facets**
of ``run.created`` (``policy_snapshot.finding_fix_strictness`` vs
``payload.workflow_profile``). Existing coverage is patch / wrap-only
via ``_maybe_emit_critique_gate_fail_findings`` callers; the uncaught
``ValidationError`` arm, the ``str(wf)`` non-string-coercion arm, and
the cross-helper shared-row-source / different-facet / read-only /
asymmetric-error-surface invariants are unpinned.

fo119 closes the gap with 4 parts spanning 20 axes (no source
changes):

* **Part A** -- ``_strictness_context`` ``fs``-input matrix, isolated
 via ``patch.object`` on ``policy_snapshot_for_run`` (5 axes):
 dict-valid HIGH/True (A1), dict-empty defaults to MEDIUM/False (A2),
 dict-invalid 3-flavour ``ValidationError`` matrix (A3),
 missing-key + explicit-``None`` converge to ``{}`` (A4),
 non-dict 6-type matrix to ``{}`` (A5).
* **Part B** -- ``_strictness_context`` real-path integration via
 ``create_run`` (5 axes): default policy round-trip (B1),
 ``run_policy_overrides`` propagation (B2), unknown ``run_id`` to
 ``{}`` (B3), ``wraps`` call-count exactly 1 (B4), idempotency
 ``==`` + freshness ``is not`` (B5).
* **Part C** -- ``_effective_universal_critique_for_run`` direct seam
 contract (5 axes): no-events seam receives ``None`` (C1),
 ``"default"`` profile round-trip (C2), real call returns
 ``EffectiveUniversalCritique`` dataclass (C3), ``str(wf)`` coercion
 on non-string ``workflow_profile`` (C4), FIRST-wins on two
 ``run.created`` rows (C5).
* **Part D** -- cross-helper KEY DIVERGENCES + invariants (5 axes):
 shared ``list_run_events`` source (D1), different facets of
 ``run.created`` (D2), neither mutates the store (D3),
 ``self._repo_root`` propagation (D4), asymmetric error surface --
 same ``rid`` raises ``ValidationError`` in one helper while the
 other returns a valid ``EffectiveUniversalCritique`` (D5).

KEY DIVERGENCES pinned across the composite:

* **3 observable outcomes through 2 input branches** --
 ``isinstance(fs, dict)`` is the SOLE branch in ``_strictness_context``;
 the True arm has TWO observable outcomes (validate-OK / raise
 ``ValidationError``), the False arm has ONE (``{}``). A refactor
 adding ``try``/``except ValidationError`` around ``model_validate``
 would silently convert the raise arm to ``{}`` and lose the
 fail-loud contract that ``_emit_critique_gate_fail_findings``
 relies on. Part A A3 pins via ``pytest.raises(ValidationError)``.
* **``.get(key)`` returns ``None`` for both missing-key AND
 explicit-``None``** -- both inputs converge through the same
 ``not isinstance(None, dict)`` branch to ``{}``. A refactor to
 ``fs["finding_fix_strictness"]`` (bracket access) would raise
 ``KeyError`` for missing-key, changing the contract. Part A A4
 pins both inputs yield the same ``{}``.
* **``str(wf)`` cast in ``workflow_profile_from_run_created_rows``**
 -- non-``None`` ``workflow_profile`` values are wrapped in
 ``str(...)`` at
 [integrator_gate.py:84](packages/hermes_orchestrator/integrator_gate.py).
 A refactor that removed ``str()`` would let an ``int`` flow
 downstream and break ``parse_universal_critique_workflow_block``'s
 ``workflow_profile_path(repo_root, profile)`` filename composition.
 Part C C4 pins via raw-row injection of ``workflow_profile=123``
 and asserting the seam receives ``"123"`` (str).
* **FIRST-wins** -- both ``policy_snapshot_for_run`` and
 ``workflow_profile_from_run_created_rows`` ``return`` inside the
 first matching iteration of their ``for row in ...`` loop. A
 refactor to last-wins or merge-all would silently change semantics.
 Part C C5 pins via 2-row injection with distinguishable
 ``workflow_profile`` values.
* **Same row source, different facets, no shared cache** -- both
 helpers call ``self._store.list_run_events(str(run_id))``
 independently (one via ``policy_snapshot_for_run``, one direct).
 A refactor that memoized the call on ``self`` would still produce
 the same outputs but change the observable call count. Part D D1
 pins shared source; the 2-call count is asserted explicitly.
* **Asymmetric error surface** -- ``_strictness_context`` can raise
 ``ValidationError``; ``_effective_universal_critique_for_run``
 always succeeds at the seam (no validation arm; the env-over-YAML
 resolver in ``effective_universal_critique`` always returns a
 fully populated ``EffectiveUniversalCritique``). Part D D5 pins
 the asymmetry via paired ``pytest.raises`` vs ``isinstance``
 assertions on the **same** ``run_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from agent_core.models.events import FindingFixStrictnessSettings, Severity
from hermes_orchestrator import pipeline as pipeline_module
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_universal_critique import EffectiveUniversalCritique


def _all_false_effective_critique() -> EffectiveUniversalCritique:
    """Construct a fully-defaulted ``EffectiveUniversalCritique`` (all-False).

    Used as the patched ``effective_universal_critique`` return value
    in Part C / Part D axes that only care about CAPTURED args, not
    the returned content. Keeping all 15 booleans False simplifies
    debugging when an assertion fires with this in scope.
    """
    return EffectiveUniversalCritique(
        impl_llm=False,
        impl_stub=False,
        impl_stage_failed_on_gate_fail=False,
        impl_emit_finding_on_gate_fail=False,
        impl_hard_block_on_gate_fail=False,
        tw_enabled=False,
        tw_llm=False,
        tw_stub=False,
        tw_stage_failed_on_gate_fail=False,
        tw_emit_finding_on_gate_fail=False,
        tw_hard_block_on_gate_fail=False,
        pll_enabled=False,
        pll_llm=False,
        pll_stub=False,
        pll_stage_failed_on_gate_fail=False,
        pll_emit_finding_on_gate_fail=False,
        pll_hard_block_on_gate_fail=False,
    )


def _inject_raw_run_created_row(
    store: Any,
    run_id: UUID,
    *,
    workflow_profile: Any,
) -> None:
    """Append a raw ``run.created`` row directly to ``InMemoryEventStore._rows``.

    Bypasses Pydantic validation in ``InMemoryEventStore.append`` so
    Part C C4 / C5 can inject non-string ``workflow_profile`` values
    (which the normal path would reject at the
    ``RunCreatedPayload(workflow_profile=...)`` step). The row shape
    matches what ``InMemoryEventStore.append`` would have produced
    -- see [packages/hermes_store/memory.py](packages/hermes_store/memory.py)
    lines 25-60 for the canonical row dict shape.
    """
    store._seq += 1  # noqa: SLF001
    store._rows.append(  # noqa: SLF001
        {
            "store_seq": store._seq,  # noqa: SLF001
            "event_id": uuid4(),
            "run_id": run_id,
            "stage_id": None,
            "task_id": None,
            "event_type": "run.created",
            "event_version": 1,
            "occurred_at": datetime.now(timezone.utc),
            "correlation_id": None,
            "idempotency_key": None,
            "actor_role_id": None,
            "previous_event_id": None,
            "payload": {
                "workflow_profile": workflow_profile,
                "policy_version": "1",
                "config_snapshot_id": str(uuid4()),
            },
            "metadata": {},
        }
    )


# -- Part A -- _strictness_context fs-input matrix (5 axes) --------------------


def test_strictness_context_fs_input_matrix_5_axis() -> None:
    """Pin ``_strictness_context`` ``fs``-input matrix via ``patch.object`` (5 axes).

    Implementation at
    [pipeline.py:554-559](packages/hermes_orchestrator/pipeline.py):

    .. code-block:: python

        snap = self.policy_snapshot_for_run(run_id)
        fs = snap.get("finding_fix_strictness")
        if isinstance(fs, dict):
            return {"finding_fix_strictness": FindingFixStrictnessSettings.model_validate(fs)}
        return {}

    Five axes cover the FULL input space: dict-valid happy path (A1),
    dict-empty defaults (A2), dict-invalid 3-flavour ``ValidationError``
    matrix (A3), ``None``-convergence (A4), non-dict 6-type matrix (A5).
    Isolation via ``patch.object(orch, "policy_snapshot_for_run",
    return_value=...)`` lets each axis inject any ``snap`` shape
    without going through ``create_run`` / Pydantic.
    """
    orch, _mem = make_dev_orchestrator()
    rid = uuid4()

    with patch.object(
        orch,
        "policy_snapshot_for_run",
        return_value={
            "finding_fix_strictness": {
                "minimum_severity_requiring_fixes": "HIGH",
                "also_require_fixes_for_low_severity": True,
            }
        },
    ):
        ctx = orch._strictness_context(rid)  # noqa: SLF001
    assert "finding_fix_strictness" in ctx, (
        f"A1: dict-valid input must yield a context with the "
        f"``finding_fix_strictness`` key. Got: {ctx!r}"
    )
    fs_obj = ctx["finding_fix_strictness"]
    assert isinstance(fs_obj, FindingFixStrictnessSettings), (
        f"A1: ``ctx['finding_fix_strictness']`` must be a "
        f"``FindingFixStrictnessSettings`` instance (NOT the raw dict). "
        f"A refactor that dropped the ``model_validate`` call would "
        f"leak the raw dict through and break attribute-access "
        f"downstream (e.g. ``ctx['finding_fix_strictness'].minimum_severity_requiring_fixes`` "
        f"in ``FindingCreatedPayload.model_validate(..., context=ctx)``). "
        f"Got type: {type(fs_obj).__name__}"
    )
    assert fs_obj.minimum_severity_requiring_fixes == Severity.HIGH, (
        f"A1: HIGH input must round-trip to ``Severity.HIGH``. Got: "
        f"{fs_obj.minimum_severity_requiring_fixes!r}"
    )
    assert fs_obj.also_require_fixes_for_low_severity is True, (
        f"A1: True input must round-trip to ``True``. Got: "
        f"{fs_obj.also_require_fixes_for_low_severity!r}"
    )

    with patch.object(
        orch,
        "policy_snapshot_for_run",
        return_value={"finding_fix_strictness": {}},
    ):
        ctx_a2 = orch._strictness_context(rid)  # noqa: SLF001
    fs_a2 = ctx_a2["finding_fix_strictness"]
    assert isinstance(fs_a2, FindingFixStrictnessSettings), (
        f"A2: empty-dict ``fs`` is dict-valid (both fields have "
        f"defaults per [packages/agent_core/models/events.py:120-131]"
        f"(packages/agent_core/models/events.py)); the result must "
        f"still wrap as ``FindingFixStrictnessSettings``. Got type: "
        f"{type(fs_a2).__name__}"
    )
    assert fs_a2.minimum_severity_requiring_fixes == Severity.MEDIUM, (
        f"A2: empty dict must yield ``Severity.MEDIUM`` (the schema "
        f"default at events.py:130). A refactor that changed the "
        f"default would silently shift the floor for every run "
        f"without explicit strictness overrides. Got: "
        f"{fs_a2.minimum_severity_requiring_fixes!r}"
    )
    assert fs_a2.also_require_fixes_for_low_severity is False, (
        f"A2: empty dict must yield ``False`` (default at events.py:131). "
        f"Got: {fs_a2.also_require_fixes_for_low_severity!r}"
    )

    bad_enum = {"finding_fix_strictness": {"minimum_severity_requiring_fixes": "BOGUS"}}
    extra_key = {"finding_fix_strictness": {"unknown_field": True}}
    wrong_type = {
        "finding_fix_strictness": {"also_require_fixes_for_low_severity": "not-a-bool"}
    }
    for label, snap in (
        ("bad-enum", bad_enum),
        ("extra-key (extra='forbid' on BasePayload)", extra_key),
        ("wrong-type-for-bool", wrong_type),
    ):
        with (
            patch.object(orch, "policy_snapshot_for_run", return_value=snap),
            pytest.raises(ValidationError) as exc_a3,
        ):
            orch._strictness_context(rid)  # noqa: SLF001
        assert "FindingFixStrictnessSettings" in str(exc_a3.value), (
            f"A3 [{label}]: ``ValidationError`` must mention "
            f"``FindingFixStrictnessSettings`` (proves the failure "
            f"came from THIS model's ``model_validate``, not some "
            f"upstream Pydantic call). A refactor that wrapped "
            f"``model_validate`` in ``try``/``except`` would silently "
            f"convert this raise to ``{{}}`` and lose the fail-loud "
            f"contract. Got: {str(exc_a3.value)[:200]!r}"
        )

    for label, snap in (
        ("missing-key (no 'finding_fix_strictness')", {}),
        ("explicit-None", {"finding_fix_strictness": None}),
    ):
        with patch.object(orch, "policy_snapshot_for_run", return_value=snap):
            ctx_a4 = orch._strictness_context(rid)  # noqa: SLF001
        assert ctx_a4 == {}, (
            f"A4 [{label}]: must converge to ``{{}}`` -- "
            f"``snap.get('finding_fix_strictness')`` returns ``None`` "
            f"for BOTH inputs and ``isinstance(None, dict)`` is False. "
            f"A refactor to ``snap['finding_fix_strictness']`` (bracket "
            f"access) would raise ``KeyError`` for the missing-key case, "
            f"breaking convergence. Got: {ctx_a4!r}"
        )

    non_dict_matrix: list[Any] = [[], "string", 123, 1.5, True, False]
    for fs_val in non_dict_matrix:
        with patch.object(
            orch,
            "policy_snapshot_for_run",
            return_value={"finding_fix_strictness": fs_val},
        ):
            ctx_a5 = orch._strictness_context(rid)  # noqa: SLF001
        assert ctx_a5 == {}, (
            f"A5: non-dict ``fs={fs_val!r}`` "
            f"(type={type(fs_val).__name__}) must yield ``{{}}`` via "
            f"the single ``isinstance(fs, dict)`` branch. A refactor "
            f"adding per-type special cases (e.g. ``isinstance(fs, (dict, "
            f"OrderedDict))``) would still match here, but a refactor "
            f"to duck-typed ``try: fs.get(...)`` would silently accept "
            f"dict-likes. Got: {ctx_a5!r}"
        )


# -- Part B -- _strictness_context real-path integration (5 axes) --------------


def test_strictness_context_real_path_integration_5_axis() -> None:
    """Pin ``_strictness_context`` real-path round-trip via ``create_run`` (5 axes).

    Validates the END-TO-END flow that Part A exercises in isolation:
    ``create_run`` builds a ``policy_snapshot``, persists a
    ``run.created`` event, ``policy_snapshot_for_run`` reads it back
    via ``model_dump(mode="json")``, and ``_strictness_context`` wraps
    the strictness dict. Each axis pins a distinct integration
    invariant.
    """
    orch_b1, _ = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    ctx_b1 = orch_b1._strictness_context(rid_b1)  # noqa: SLF001
    fs_b1 = ctx_b1.get("finding_fix_strictness")
    assert isinstance(fs_b1, FindingFixStrictnessSettings), (
        f"B1: ``create_run('default')`` without overrides must yield "
        f"a context with a ``FindingFixStrictnessSettings`` instance "
        f"reflecting the bare defaults. A refactor that lost the "
        f"strictness layer in ``merge_policy_snapshot`` would yield "
        f"``{{}}``. Got: {ctx_b1!r}"
    )
    assert fs_b1.minimum_severity_requiring_fixes == Severity.MEDIUM, (
        f"B1: bare-default severity must be MEDIUM (set in "
        f"[packages/hermes_orchestrator/merge.py:37-41]"
        f"(packages/hermes_orchestrator/merge.py) when no layer "
        f"provides strictness). Got: "
        f"{fs_b1.minimum_severity_requiring_fixes!r}"
    )
    assert fs_b1.also_require_fixes_for_low_severity is False, (
        f"B1: bare-default low-severity flag must be False. Got: "
        f"{fs_b1.also_require_fixes_for_low_severity!r}"
    )

    orch_b2, _ = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run(
        "default",
        run_policy_overrides={
            "finding_fix_strictness": {
                "minimum_severity_requiring_fixes": "BLOCKER",
                "also_require_fixes_for_low_severity": True,
            }
        },
    )
    ctx_b2 = orch_b2._strictness_context(rid_b2)  # noqa: SLF001
    fs_b2 = ctx_b2["finding_fix_strictness"]
    assert fs_b2.minimum_severity_requiring_fixes == Severity.BLOCKER, (
        f"B2: ``run_policy_overrides`` must propagate through "
        f"``merge_policy_snapshot`` (run-overrides layer applied LAST) "
        f"into ``policy_snapshot.finding_fix_strictness``, read back "
        f"via ``policy_snapshot_for_run``, and wrapped by "
        f"``_strictness_context``. A refactor that dropped the "
        f"``run_overrides`` layer in ``merge_policy_snapshot`` would "
        f"silently return MEDIUM here -- a regression that "
        f"``_emit_critique_gate_fail_findings`` would not catch since "
        f"``MEDIUM`` strictness is still valid. Got: "
        f"{fs_b2.minimum_severity_requiring_fixes!r}"
    )
    assert fs_b2.also_require_fixes_for_low_severity is True, (
        f"B2: override of ``also_require_fixes_for_low_severity=True`` "
        f"must propagate. Got: "
        f"{fs_b2.also_require_fixes_for_low_severity!r}"
    )

    orch_b3, _ = make_dev_orchestrator()
    ctx_b3 = orch_b3._strictness_context(uuid4())  # noqa: SLF001
    assert ctx_b3 == {}, (
        f"B3: unknown ``run_id`` (factory without ``create_run``) "
        f"must return ``{{}}`` because ``policy_snapshot_for_run`` "
        f"falls through to ``return {{}}`` (no ``run.created`` row) "
        f"and ``.get('finding_fix_strictness')`` returns ``None`` -> "
        f"non-dict branch -> ``{{}}``. Pins the upstream-empty "
        f"fallback. Got: {ctx_b3!r}"
    )

    orch_b4, _ = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    with patch.object(
        orch_b4,
        "policy_snapshot_for_run",
        wraps=orch_b4.policy_snapshot_for_run,
    ) as mock_snap:
        orch_b4._strictness_context(rid_b4)  # noqa: SLF001
    assert mock_snap.call_count == 1, (
        f"B4: ONE invocation of ``_strictness_context`` must cause "
        f"EXACTLY ONE call to ``policy_snapshot_for_run``. A refactor "
        f"that added a defensive re-read (e.g. checking idempotency) "
        f"would change the read count and amplify event-store I/O in "
        f"hot paths. Got call_count={mock_snap.call_count}"
    )
    assert mock_snap.call_args.args == (rid_b4,), (
        f"B4: the call must pass the ``run_id`` positionally as the "
        f"sole argument. Got args: {mock_snap.call_args.args!r}"
    )

    orch_b5, _ = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    ctx_b5_first = orch_b5._strictness_context(rid_b5)  # noqa: SLF001
    ctx_b5_second = orch_b5._strictness_context(rid_b5)  # noqa: SLF001
    assert ctx_b5_first == ctx_b5_second, (
        f"B5: two sequential calls with the SAME ``run_id`` must "
        f"yield ``==``-equal results (idempotency). Got first="
        f"{ctx_b5_first!r} second={ctx_b5_second!r}"
    )
    assert (
        ctx_b5_first["finding_fix_strictness"]
        is not ctx_b5_second["finding_fix_strictness"]
    ), (
        f"B5 KEY DIVERGENCE: the ``FindingFixStrictnessSettings`` "
        f"instances must NOT be the same object (``is not``). Pins "
        f"that ``model_validate`` constructs a FRESH instance per "
        f"call. A refactor that cached the wrapped instance on "
        f"``self`` (or returned a singleton) would still satisfy "
        f"``==`` but break ``is not``, with subtle aliasing risk if "
        f"downstream callers mutated the instance. Got: "
        f"id(first)={id(ctx_b5_first['finding_fix_strictness'])} "
        f"id(second)={id(ctx_b5_second['finding_fix_strictness'])}"
    )


# -- Part C -- _effective_universal_critique_for_run seam (5 axes) -------------


def test_effective_universal_critique_for_run_seam_5_axis() -> None:
    """Pin ``_effective_universal_critique_for_run`` direct seam (5 axes).

    Implementation at
    [pipeline.py:700-702](packages/hermes_orchestrator/pipeline.py):

    .. code-block:: python

        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        return effective_universal_critique(self._repo_root, wf)

    Five axes pin the seam: no-events -> ``None`` (C1),
    ``create_run('default')`` -> ``"default"`` (C2), real return type
    is ``EffectiveUniversalCritique`` (C3), non-string
    ``workflow_profile`` is ``str()``-coerced (C4), FIRST-wins on
    multiple ``run.created`` (C5). Uses
    ``patch.object(pipeline_module, "effective_universal_critique",
    side_effect=...)`` to capture the args the seam receives without
    coupling to the real YAML / env resolution.
    """
    captured_args: dict[str, Any] = {}

    def fake_euc(repo_root: Any, wf: Any) -> EffectiveUniversalCritique:
        captured_args["repo_root"] = repo_root
        captured_args["wf"] = wf
        return _all_false_effective_critique()

    orch_c1, _ = make_dev_orchestrator()
    captured_args.clear()
    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc
    ):
        result_c1 = orch_c1._effective_universal_critique_for_run(uuid4())  # noqa: SLF001
    assert captured_args["wf"] is None, (
        f"C1: with NO ``run.created`` rows, "
        f"``workflow_profile_from_run_created_rows`` returns ``None`` "
        f"(no match in the for-loop), and the seam must receive "
        f"``None`` (NOT empty string or omitted positional). A "
        f"refactor that converted ``None`` -> ``''`` would change "
        f"how ``parse_universal_critique_workflow_block`` resolves "
        f"the missing-profile arm. Got: wf={captured_args['wf']!r}"
    )
    assert isinstance(result_c1, EffectiveUniversalCritique), (
        f"C1: the patched ``effective_universal_critique`` return "
        f"value must propagate through unchanged. Got type: "
        f"{type(result_c1).__name__}"
    )

    orch_c2, _ = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    captured_args.clear()
    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc
    ):
        orch_c2._effective_universal_critique_for_run(rid_c2)  # noqa: SLF001
    assert captured_args["wf"] == "default", (
        f"C2: after ``create_run('default')``, the seam must receive "
        f"``'default'`` (the workflow profile name passed to "
        f"``create_run``, stored in ``run.created`` ``payload.workflow_profile``). "
        f"A refactor that dropped the profile from the payload would "
        f"silently send ``None`` here. Got: wf={captured_args['wf']!r}"
    )
    assert isinstance(captured_args["wf"], str), (
        f"C2: for a string ``workflow_profile``, the seam receives a "
        f"``str`` (no coercion needed -- pin that ``str(wf) if wf is "
        f"not None`` is a NO-OP for strings, not a re-wrap that could "
        f"change identity). Got type: {type(captured_args['wf']).__name__}"
    )

    orch_c3, _ = make_dev_orchestrator()
    result_c3 = orch_c3._effective_universal_critique_for_run(uuid4())  # noqa: SLF001
    assert isinstance(result_c3, EffectiveUniversalCritique), (
        f"C3: REAL call (no patch) must return an "
        f"``EffectiveUniversalCritique`` dataclass instance. A "
        f"refactor that wrapped the result in a dict for back-compat "
        f"would break callers like ``_maybe_emit_critique_gate_fail_findings`` "
        f"that do ``eff.impl_emit_finding_on_gate_fail`` attribute "
        f"access. Got type: {type(result_c3).__name__}"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = uuid4()
    _inject_raw_run_created_row(mem_c4, rid_c4, workflow_profile=123)
    captured_args.clear()
    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc
    ):
        orch_c4._effective_universal_critique_for_run(rid_c4)  # noqa: SLF001
    assert captured_args["wf"] == "123", (
        f"C4 KEY DIVERGENCE: non-string ``workflow_profile=123`` must "
        f"be ``str()``-coerced to ``'123'`` at "
        f"[integrator_gate.py:84](packages/hermes_orchestrator/integrator_gate.py): "
        f"``return str(wf) if wf is not None else None``. A refactor "
        f"that dropped the ``str()`` cast would let ``int`` flow "
        f"downstream and break ``workflow_profile_path(repo_root, "
        f"profile)`` filename composition. Got: wf={captured_args['wf']!r}"
    )
    assert isinstance(captured_args["wf"], str), (
        f"C4 KEY DIVERGENCE: the resulting type must be ``str``, NOT "
        f"``int`` (proves the coercion actually fired). Got type: "
        f"{type(captured_args['wf']).__name__}"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = uuid4()
    _inject_raw_run_created_row(mem_c5, rid_c5, workflow_profile="first")
    _inject_raw_run_created_row(mem_c5, rid_c5, workflow_profile="second")
    captured_args.clear()
    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc
    ):
        orch_c5._effective_universal_critique_for_run(rid_c5)  # noqa: SLF001
    assert captured_args["wf"] == "first", (
        f"C5 KEY DIVERGENCE: with TWO ``run.created`` rows, the "
        f"FIRST one's ``workflow_profile`` wins -- "
        f"``workflow_profile_from_run_created_rows`` ``return``s "
        f"inside the for-loop on the first match. A refactor to "
        f"last-wins or merge-all would yield ``'second'`` here. Got: "
        f"wf={captured_args['wf']!r}"
    )


# -- Part D -- cross-helper KEY DIVERGENCES + invariants (5 axes) --------------


def test_cross_helper_key_divergences_5_axis() -> None:
    """Pin cross-helper KEY DIVERGENCES between ``_strictness_context`` and
    ``_effective_universal_critique_for_run`` (5 axes).

    Both helpers read from the SAME row source via different code
    paths (one through ``policy_snapshot_for_run`` -> ``list_run_events``,
    the other directly through ``list_run_events``) and consume
    DIFFERENT facets of ``run.created``. Five axes pin: shared
    source (D1), different facets (D2), read-only (D3),
    ``self._repo_root`` propagation (D4), asymmetric error surface
    (D5).
    """
    orch_d1, _ = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    with patch.object(
        orch_d1._store,  # noqa: SLF001
        "list_run_events",
        wraps=orch_d1._store.list_run_events,  # noqa: SLF001
    ) as mock_lre:
        orch_d1._strictness_context(rid_d1)  # noqa: SLF001
        orch_d1._effective_universal_critique_for_run(rid_d1)  # noqa: SLF001
    assert mock_lre.call_count == 2, (
        f"D1: calling BOTH helpers on the same ``rid`` must yield "
        f"EXACTLY 2 calls to ``self._store.list_run_events`` -- one "
        f"via ``policy_snapshot_for_run`` -> ``list_run_events`` "
        f"(for ``_strictness_context``), one direct (for "
        f"``_effective_universal_critique_for_run``). A refactor that "
        f"memoized the call on ``self`` would still produce the same "
        f"outputs but change this count to 1 (or 0 on second call), "
        f"hiding an opportunity for batched reads. Got call_count="
        f"{mock_lre.call_count}"
    )
    for i, call in enumerate(mock_lre.call_args_list):
        assert call.args == (str(rid_d1),), (
            f"D1: call {i} must pass ``str(rid)`` positionally as the "
            f"sole argument (NOT the ``UUID`` object). Got args: "
            f"{call.args!r}"
        )

    orch_d2, _ = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run(
        "default",
        run_policy_overrides={
            "finding_fix_strictness": {
                "minimum_severity_requiring_fixes": "HIGH",
                "also_require_fixes_for_low_severity": True,
            }
        },
    )
    ctx_d2 = orch_d2._strictness_context(rid_d2)  # noqa: SLF001
    captured_d2: dict[str, Any] = {}

    def fake_euc_d2(repo_root: Any, wf: Any) -> EffectiveUniversalCritique:
        captured_d2["wf"] = wf
        return _all_false_effective_critique()

    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc_d2
    ):
        orch_d2._effective_universal_critique_for_run(rid_d2)  # noqa: SLF001
    fs_d2 = ctx_d2["finding_fix_strictness"]
    assert fs_d2.minimum_severity_requiring_fixes == Severity.HIGH, (
        f"D2: ``_strictness_context`` consumes the "
        f"``policy_snapshot.finding_fix_strictness`` facet of "
        f"``run.created`` -- the strictness override (HIGH/True) "
        f"flows through here, NOT the workflow_profile. Got: "
        f"{fs_d2.minimum_severity_requiring_fixes!r}"
    )
    assert captured_d2["wf"] == "default", (
        f"D2: ``_effective_universal_critique_for_run`` consumes the "
        f"``payload.workflow_profile`` facet -- it receives "
        f"``'default'`` (the workflow profile passed to ``create_run``) "
        f"and is UNAFFECTED by the strictness override (which lives "
        f"on a different facet). Pins independence of the two facets "
        f"on the SAME ``run.created`` row. Got: wf={captured_d2['wf']!r}"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    rows_before = len(mem_d3._rows)  # noqa: SLF001
    orch_d3._strictness_context(rid_d3)  # noqa: SLF001
    orch_d3._effective_universal_critique_for_run(rid_d3)  # noqa: SLF001
    rows_after = len(mem_d3._rows)  # noqa: SLF001
    assert rows_after == rows_before, (
        f"D3: calling BOTH helpers must NOT mutate the event store -- "
        f"both are read-only resolvers. A refactor that appended a "
        f"``RUN_STATUS_RESOLVED`` event (or similar audit trail) would "
        f"silently grow the store with side-effecting reads. Got: "
        f"rows_before={rows_before} rows_after={rows_after} (delta="
        f"{rows_after - rows_before})"
    )

    orch_d4, _ = make_dev_orchestrator()
    captured_d4: dict[str, Any] = {}

    def fake_euc_d4(repo_root: Any, wf: Any) -> EffectiveUniversalCritique:
        captured_d4["repo_root"] = repo_root
        captured_d4["wf"] = wf
        return _all_false_effective_critique()

    with patch.object(
        pipeline_module, "effective_universal_critique", side_effect=fake_euc_d4
    ):
        orch_d4._effective_universal_critique_for_run(uuid4())  # noqa: SLF001
    assert captured_d4["repo_root"] == orch_d4.repo_root, (
        f"D4 KEY DIVERGENCE: ``effective_universal_critique`` must "
        f"receive ``self._repo_root`` as the FIRST positional argument "
        f"(per [pipeline.py:702](packages/hermes_orchestrator/pipeline.py) "
        f"``effective_universal_critique(self._repo_root, wf)``). A "
        f"refactor that hardcoded a path or used a module-level global "
        f"would break this. Got: repo_root={captured_d4['repo_root']!r} "
        f"vs orch.repo_root={orch_d4.repo_root!r}"
    )

    orch_d5, _ = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    bad_snap = {
        "finding_fix_strictness": {"minimum_severity_requiring_fixes": "BOGUS"}
    }
    with patch.object(
        orch_d5, "policy_snapshot_for_run", return_value=bad_snap
    ):
        with pytest.raises(ValidationError):
            orch_d5._strictness_context(rid_d5)  # noqa: SLF001
        result_d5 = orch_d5._effective_universal_critique_for_run(rid_d5)  # noqa: SLF001
    assert isinstance(result_d5, EffectiveUniversalCritique), (
        f"D5 KEY DIVERGENCE: asymmetric error surface on the SAME "
        f"``rid``. With ``policy_snapshot_for_run`` patched to return "
        f"an invalid strictness dict: ``_strictness_context`` raises "
        f"``ValidationError`` (uncaught) WHILE "
        f"``_effective_universal_critique_for_run`` -- which bypasses "
        f"``policy_snapshot_for_run`` entirely and reads "
        f"``payload.workflow_profile`` directly -- succeeds and returns "
        f"a valid ``EffectiveUniversalCritique``. Pins that the two "
        f"helpers have INDEPENDENT failure modes despite sharing a "
        f"row source. Got type: {type(result_d5).__name__}"
    )
