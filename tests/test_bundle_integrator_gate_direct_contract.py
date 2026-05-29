"""_emit_bundle_integrator_gate`` direct contract composite."""


from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from agent_core.models import EventType, Verdict
from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


_GATE_EMITTED = EventType.GATE_DECISION_EMITTED.value
_EXPECTED_META_KEYS = {
    "integrator_gate",
    "bundle_id",
    "bundle_title",
    "integrator_score",
    "min_score_to_pass",
    "integrator_project_tags",
    "integrator_bundle_tags",
    "integrator_matched_tags",
    "bundle_compatibility_ranking",
    "bundle_compatibility_ranking_count",
    "selected_bundle_rank",
    "bundle_outcome",
}


def _gate_rows(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    """Return all ``gate.decision.emitted`` rows for the run in store order."""
    return [
        r for r in mem.list_run_events(str(rid)) if r.get("event_type") == _GATE_EMITTED
    ]


def _gate_meta(row: dict[str, Any]) -> dict[str, Any]:
    """Return ``metadata`` dict for an integrator gate row (defaults to ``{}``)."""
    return dict(row.get("metadata") or {})


def _gate_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` dict for an integrator gate row (defaults to ``{}``)."""
    return dict(row.get("payload") or {})


def _make_fake_mi_class(
    *,
    score: float = 1.0,
    passes: bool = True,
    min_score: float = 0.7,
) -> tuple[MagicMock, MagicMock]:
    """Build a ``(class_mock, instance_mock)`` pair for ``ModuleIntegrator``.

    The class mock returns ``instance_mock`` when invoked via
    ``ModuleIntegrator(min_score_to_pass=...)``; the instance exposes
    concrete numeric values for ``score_fit`` / ``passes_gate`` /
    ``min_score_to_pass`` so the downstream ``model_dump(mode="json")``
    serialization in :class:`InMemoryEventStore.append` succeeds.
    """
    mi_instance = MagicMock()
    mi_instance.score_fit.return_value = score
    mi_instance.passes_gate.return_value = passes
    mi_instance.min_score_to_pass = min_score
    class_mock = MagicMock(return_value=mi_instance)
    return class_mock, mi_instance


def test_bundle_integrator_gate_thresholds_absent_and_or_gate_5_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin thresholds.yaml-absent arm + OR-gate guard + env-vs-import ordering.

    A1 -- thresholds.yaml absent + workflow-on -> no emit (uncovered today).
    A2 -- env force-on + thresholds.yaml absent -> still no emit (env on
    cannot rescue missing thresholds; absent-arm sits AFTER env force-on).
    A3 -- env kill-switch -> ModuleIntegrator NOT constructed (lazy-import
    seam pin; would silently regress under a "hoist import to module-level"
    refactor that moved instantiation before the kill switch).
    A4 -- all gates off + env unset -> no emit (canonical control).
    A5 -- workflow YAML on + loader False -> emit via ``wf_on`` alone.
    """
    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch.object(Path, "is_file", return_value=False),
    ):
        orch_a1._emit_bundle_integrator_gate(rid_a1)  # noqa: SLF001
    assert _gate_rows(mem_a1, rid_a1) == [], (
        "A1: thresholds.yaml absent + workflow-on (`integrator_gate_on`) -> "
        "NO emit. Pins the absent-arm at pipeline.py:1497-1498 "
        "(uncovered today; OR-gate accepts wf_on alone but the absent check "
        "fires AFTER the OR-gate, so workflow-on cannot rescue missing thresholds)"
    )

    monkeypatch.setenv("HERMES_EMIT_INTEGRATOR_GATE", "1")
    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch.object(Path, "is_file", return_value=False),
    ):
        orch_a2._emit_bundle_integrator_gate(rid_a2)  # noqa: SLF001
    assert _gate_rows(mem_a2, rid_a2) == [], (
        "A2: env `HERMES_EMIT_INTEGRATOR_GATE=1` (force-on) + thresholds.yaml "
        "absent -> STILL no emit. Pins the absent-arm sits AFTER the env "
        "force-on check at pipeline.py:1494-1498 (env force-on cannot "
        "rescue missing thresholds; a refactor that moved the absent check "
        "BEFORE the env force-on would silently flip this from no-emit "
        "to emit-on-env)"
    )

    monkeypatch.setenv("HERMES_EMIT_INTEGRATOR_GATE", "0")
    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("integrator_gate_on")
    class_spy_a3, _ = _make_fake_mi_class()
    with patch("hermes_extensions.phase2.ModuleIntegrator", class_spy_a3):
        orch_a3._emit_bundle_integrator_gate(rid_a3)  # noqa: SLF001
    assert class_spy_a3.call_count == 0, (
        f"A3: env kill-switch `HERMES_EMIT_INTEGRATOR_GATE=0` short-circuits "
        f"BEFORE the lazy `from hermes_extensions.phase2 import ModuleIntegrator` "
        f"+ subsequent `ModuleIntegrator(min_score_to_pass=...)` at "
        f"pipeline.py:1486-1500; got class_spy_a3.call_count="
        f"{class_spy_a3.call_count}. A 'move the kill-switch below the "
        "constructor' refactor would silently increment this to 1"
    )
    assert _gate_rows(mem_a3, rid_a3) == [], (
        "A3 cross-cut: kill-switch also produces zero emitted rows"
    )

    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)
    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch_a4._emit_bundle_integrator_gate(rid_a4)  # noqa: SLF001
    assert _gate_rows(mem_a4, rid_a4) == [], (
        "A4: env unset + yaml_on=False + wf_on=False (default workflow has "
        "`integrator_gate.enabled: false`) -> OR-gate at pipeline.py:1494-1495 "
        "returns. Canonical all-off control pin"
    )

    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)
    orch_a5, mem_a5 = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("integrator_gate_on")
    with patch(
        "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch_a5._emit_bundle_integrator_gate(rid_a5)  # noqa: SLF001
    assert len(_gate_rows(mem_a5, rid_a5)) == 1, (
        "A5: env unset + yaml_on=False + wf_on=True (`integrator_gate_on` "
        "profile) -> OR-gate accepts wf_on alone; thresholds.yaml present "
        "(real config) -> exactly 1 emit. Pins the `yaml_on or wf_on` arm "
        "structure (overlapping existing coverage, but anchors fo107 Part A "
        "to the full guard ladder)"
    )


def test_bundle_integrator_gate_project_tags_three_arm_ladder_5_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin the project_tags 3-arm ladder + ``is not None`` semantics.

    The ladder at pipeline.py:1505-1510 has three arms:
    * ``project_override is not None`` -> use override (B1, B4).
    * ``elif bundle_tags:`` -> ``list(bundle_tags)`` (B2).
    * ``else:`` -> ``[bundle_id]`` singleton fallback (B3; uncovered today).

    B5 pins the structural boundary between B3 (None) and B4 ([]).
    """
    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)

    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=["foo", "bar"],
        ),
    ):
        orch_b1._emit_bundle_integrator_gate(rid_b1)  # noqa: SLF001
    meta_b1 = _gate_meta(_gate_rows(mem_b1, rid_b1)[0])
    assert meta_b1["integrator_project_tags"] == ["foo", "bar"], (
        f"B1: project_override non-None non-empty ([`foo`, `bar`]) -> "
        f"project_tags == override; got "
        f"{meta_b1.get('integrator_project_tags')!r}. Pins the first arm "
        "of the ladder at pipeline.py:1505-1506"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=None,
        ),
    ):
        orch_b2._emit_bundle_integrator_gate(rid_b2)  # noqa: SLF001
    meta_b2 = _gate_meta(_gate_rows(mem_b2, rid_b2)[0])
    assert meta_b2["integrator_project_tags"] == ["auth", "rbac"], (
        f"B2: project_override None + bundle_tags non-empty "
        f"([`auth`, `rbac`] from `auth-rbac-starter`) -> project_tags == "
        f"list(bundle_tags); got {meta_b2.get('integrator_project_tags')!r}. "
        "Pins the `elif bundle_tags:` arm at pipeline.py:1507-1508"
    )
    assert (
        meta_b2["integrator_project_tags"] is not meta_b2["integrator_bundle_tags"]
    ), (
        "B2 cross-cut: `list(bundle_tags)` makes a COPY (not alias); a "
        "refactor to `project_tags = bundle_tags` would still pass value "
        "equality but break this identity check, signalling shared-mutation risk"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=None,
        ),
        patch(
            "hermes_orchestrator.pipeline.load_bundle_tags_for_bundle_id",
            return_value=[],
        ),
    ):
        orch_b3._emit_bundle_integrator_gate(rid_b3)  # noqa: SLF001
    meta_b3 = _gate_meta(_gate_rows(mem_b3, rid_b3)[0])
    assert meta_b3["integrator_project_tags"] == ["auth-rbac-starter"], (
        f"B3: project_override None + bundle_tags empty -> project_tags == "
        f"[bundle_id] singleton fallback ([`auth-rbac-starter`]); got "
        f"{meta_b3.get('integrator_project_tags')!r}. Closes the singleton-"
        "fallback gap at pipeline.py:1509-1510 (uncovered today because "
        "production YAML always supplies bundle tags via `auth-rbac-starter`)"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=[],
        ),
    ):
        orch_b4._emit_bundle_integrator_gate(rid_b4)  # noqa: SLF001
    meta_b4 = _gate_meta(_gate_rows(mem_b4, rid_b4)[0])
    assert meta_b4["integrator_project_tags"] == [], (
        f"B4: project_override == [] (non-None empty list, structurally "
        f"unreachable from production YAML since `parse_integrator_gate_"
        f"project_tags` collapses empty lists to None via `return out or "
        f"None` at integrator_gate.py:188-189) -> project_tags == [] "
        f"empty override; got {meta_b4.get('integrator_project_tags')!r}. "
        "**KEY PIN**: the pipeline guard at pipeline.py:1505 is `is not "
        "None`, NOT `if project_override:` truthy. A refactor to truthy "
        "guard would fall through to the bundle_tags arm and surface "
        "[`auth`, `rbac`] instead of [], silently flipping behavior"
    )

    assert meta_b3["integrator_project_tags"] != meta_b4["integrator_project_tags"], (
        f"B5: B3 (`None` override + bundle_tags empty -> [bundle_id]) and B4 "
        f"([] override -> []) produce DIFFERENT outputs given the same "
        f"bundle_tags=[] shape; got B3={meta_b3['integrator_project_tags']!r}, "
        f"B4={meta_b4['integrator_project_tags']!r}. Pins the structural "
        "boundary: None -> ladder continues; [] -> ladder stops. A regression "
        "to 'treat None and [] equivalently' would silently collapse both "
        "arms to the same singleton fallback"
    )


def test_bundle_integrator_gate_profile_shape_and_matched_tags_filter_5_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin the profile-dict conditional ``bundle_tags`` key + ``matched_tags``
    case-fold + whitespace filter.

    C1/C2 spy ``ModuleIntegrator.score_fit`` to inspect the profile arg shape.
    C3/C4/C5 inspect the emitted ``metadata.integrator_matched_tags``.
    """
    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)

    class_spy_c1, mi_c1 = _make_fake_mi_class()
    orch_c1, _ = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch("hermes_extensions.phase2.ModuleIntegrator", class_spy_c1),
    ):
        orch_c1._emit_bundle_integrator_gate(rid_c1)  # noqa: SLF001
    profile_c1 = mi_c1.score_fit.call_args_list[0].args[1]
    assert set(profile_c1.keys()) == {"tags", "bundle_tags"}, (
        f"C1: bundle_tags non-empty ([`auth`, `rbac`]) -> score_fit receives "
        f"a 2-key profile {{`tags`, `bundle_tags`}}; got "
        f"{set(profile_c1.keys())!r}. Pins the `if bundle_tags:` arm at "
        "pipeline.py:1512-1513"
    )
    assert profile_c1["bundle_tags"] == ["auth", "rbac"], (
        f"C1 cross-cut: profile.bundle_tags == catalog tags; got "
        f"{profile_c1['bundle_tags']!r}"
    )

    class_spy_c2, mi_c2 = _make_fake_mi_class(score=0.0, passes=False)
    orch_c2, _ = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.load_bundle_tags_for_bundle_id",
            return_value=[],
        ),
        patch("hermes_extensions.phase2.ModuleIntegrator", class_spy_c2),
    ):
        orch_c2._emit_bundle_integrator_gate(rid_c2)  # noqa: SLF001
    profile_c2 = mi_c2.score_fit.call_args_list[0].args[1]
    assert set(profile_c2.keys()) == {"tags"}, (
        f"C2: bundle_tags empty -> score_fit receives a 1-key profile "
        f"{{`tags`}} only; got {set(profile_c2.keys())!r}. Pins the `else:` "
        "arm at pipeline.py:1514-1515 omits the `bundle_tags` key entirely "
        "(a refactor that always included `bundle_tags=[]` would break the "
        "legacy-heuristic branch in phase2.py:47-63 which checks "
        "`isinstance(bundle_tags_raw, list) and bundle_tags_raw`)"
    )
    assert "bundle_tags" not in profile_c2, (
        "C2 cross-cut: explicit `bundle_tags not in profile` (rename-resistant)"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=["AUTH", "RBAC"],
        ),
    ):
        orch_c3._emit_bundle_integrator_gate(rid_c3)  # noqa: SLF001
    meta_c3 = _gate_meta(_gate_rows(mem_c3, rid_c3)[0])
    assert meta_c3["integrator_matched_tags"] == ["auth", "rbac"], (
        f"C3: case-fold match -- project_tags=[`AUTH`, `RBAC`] vs bundle_tags="
        f"[`auth`, `rbac`] -> matched_tags=[`auth`, `rbac`] sorted lowercase; "
        f"got {meta_c3.get('integrator_matched_tags')!r}. Pins `str(t).lower()` "
        "applied to BOTH pset and bset at pipeline.py:1518-1519"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=["auth", "   ", "rbac"],
        ),
    ):
        orch_c4._emit_bundle_integrator_gate(rid_c4)  # noqa: SLF001
    meta_c4 = _gate_meta(_gate_rows(mem_c4, rid_c4)[0])
    assert meta_c4["integrator_matched_tags"] == ["auth", "rbac"], (
        f"C4: whitespace-only tag filter -- project_tags=[`auth`, `   `, "
        f"`rbac`] -> pset excludes `   ` via `if str(t).strip()` guard; "
        f"matched_tags=[`auth`, `rbac`]; got "
        f"{meta_c4.get('integrator_matched_tags')!r}. Pins the strip-filter "
        "at pipeline.py:1518 (would silently break under a refactor that "
        "dropped the `if str(t).strip()` predicate)"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("integrator_gate_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
            return_value=False,
        ),
        patch(
            "hermes_orchestrator.pipeline.parse_integrator_gate_project_tags",
            return_value=["auth", "rbac"],
        ),
        patch(
            "hermes_orchestrator.pipeline.load_bundle_tags_for_bundle_id",
            return_value=[],
        ),
    ):
        orch_c5._emit_bundle_integrator_gate(rid_c5)  # noqa: SLF001
    meta_c5 = _gate_meta(_gate_rows(mem_c5, rid_c5)[0])
    assert meta_c5["integrator_matched_tags"] == [], (
        f"C5: bundle_tags empty -> matched_tags=[] via short-circuit "
        f"(`sorted(pset & bset) if bundle_tags else []`); got "
        f"{meta_c5.get('integrator_matched_tags')!r}. Pins the `if bundle_tags "
        "else []` guard at pipeline.py:1520 (NOT the intersection result -- "
        "even though project_tags=[`auth`, `rbac`] match the bundle catalog, "
        "the empty bundle_tags input short-circuits before intersection)"
    )


def test_bundle_integrator_gate_pass_fail_payload_divergence_5_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin PASS-vs-FAIL payload divergence + emit shape.

    D4 is the **highest-value pin** in fo107: the explicit
    ``unanimous_pass_required=False`` parameter in both branches overrides
    the Pydantic default of ``True``. A 'remove the explicit param to use
    default' refactor would silently flip the field from False to True,
    invisible to callers but materially different in downstream gate logic.
    """
    monkeypatch.delenv("HERMES_EMIT_INTEGRATOR_GATE", raising=False)

    orch_pass, mem_pass = make_dev_orchestrator()
    rid_pass = orch_pass.create_run("integrator_gate_on")
    with patch(
        "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch_pass._emit_bundle_integrator_gate(rid_pass)  # noqa: SLF001
    pass_rows = _gate_rows(mem_pass, rid_pass)
    assert len(pass_rows) == 1, (
        f"D PASS setup: exactly 1 emit; got {len(pass_rows)}"
    )
    pass_payload = _gate_payload(pass_rows[0])
    pass_meta = _gate_meta(pass_rows[0])

    orch_fail, mem_fail = make_dev_orchestrator()
    rid_fail = orch_fail.create_run("integrator_gate_mismatch")
    with patch(
        "hermes_orchestrator.pipeline.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch_fail._emit_bundle_integrator_gate(rid_fail)  # noqa: SLF001
    fail_rows = _gate_rows(mem_fail, rid_fail)
    assert len(fail_rows) == 1, (
        f"D FAIL setup: exactly 1 emit; got {len(fail_rows)}"
    )
    fail_payload = _gate_payload(fail_rows[0])
    fail_meta = _gate_meta(fail_rows[0])

    assert pass_payload.get("verdict") in (Verdict.PASS, "PASS"), (
        f"D1: PASS verdict on `integrator_gate_on` (score 1.0 >= 0.7); "
        f"got {pass_payload.get('verdict')!r}"
    )
    assert pass_payload.get("failure_reason_code") is None, (
        f"D1: PASS payload has NO `failure_reason_code` (Pydantic default "
        f"None; PASS branch at pipeline.py:1532-1536 does NOT set it); "
        f"got {pass_payload.get('failure_reason_code')!r}. The "
        "`fail_implies_signals` validator at events.py:411-415 would raise "
        "if PASS had a non-None failure_reason_code, so this also pins the "
        "validator contract"
    )

    assert fail_payload.get("verdict") in (Verdict.FAIL, "FAIL"), (
        f"D2: FAIL verdict on `integrator_gate_mismatch` (project_tags="
        f"[billing, stripe] vs bundle_tags=[auth, rbac] -> score 0.0 < 0.7); "
        f"got {fail_payload.get('verdict')!r}"
    )
    assert fail_payload.get("failure_reason_code") == "integrator_below_threshold", (
        f"D2: FAIL payload has LITERAL `failure_reason_code == "
        f"'integrator_below_threshold'`; got "
        f"{fail_payload.get('failure_reason_code')!r}. Pins the exact string "
        "at pipeline.py:1542 (a rename to `integrator_score_below_threshold` "
        "or similar would silently break downstream consumers that match on "
        "this exact code)"
    )

    assert pass_payload.get("stage_name") == "bundle_compatibility", (
        f"D3 PASS: stage_name literal == 'bundle_compatibility'; got "
        f"{pass_payload.get('stage_name')!r}"
    )
    assert fail_payload.get("stage_name") == "bundle_compatibility", (
        f"D3 FAIL: stage_name literal == 'bundle_compatibility'; got "
        f"{fail_payload.get('stage_name')!r}. Pins the identical literal "
        "at pipeline.py:1533, 1539 (a refactor that split into "
        "`bundle_compatibility_pass` / `bundle_compatibility_fail` stages "
        "would silently break this)"
    )

    assert pass_payload.get("unanimous_pass_required") is False, (
        f"D4 PASS: `unanimous_pass_required is False` EXPLICIT in PASS "
        f"branch; got {pass_payload.get('unanimous_pass_required')!r}. "
        "**KEY PIN**: `GateDecisionEmittedPayload.unanimous_pass_required` "
        "has Pydantic default True (events.py:398); the PASS branch at "
        "pipeline.py:1535 sets it EXPLICITLY to False, overriding the "
        "default. A refactor that removed the explicit param would silently "
        "flip the field from False to True"
    )
    assert fail_payload.get("unanimous_pass_required") is False, (
        f"D4 FAIL: `unanimous_pass_required is False` EXPLICIT in FAIL "
        f"branch; got {fail_payload.get('unanimous_pass_required')!r}. "
        "Mirror of D4 PASS at pipeline.py:1541 -- same explicit-False contract "
        "across BOTH branches (consistent gate-decision semantics)"
    )

    assert set(pass_meta.keys()) == _EXPECTED_META_KEYS, (
        f"D5 PASS: gate_meta shape exact match; got keys="
        f"{set(pass_meta.keys())!r}, expected={_EXPECTED_META_KEYS!r}. Pins "
        "the rename-resistant metadata contract at pipeline.py:1521-1530"
    )
    assert set(fail_meta.keys()) == _EXPECTED_META_KEYS, (
        f"D5 FAIL: gate_meta shape exact match in FAIL branch; got "
        f"keys={set(fail_meta.keys())!r}, expected={_EXPECTED_META_KEYS!r}. "
        "Pins identical metadata shape across PASS and FAIL branches "
        "(metadata is built BEFORE the `if ok:` branch, so the shape must "
        "stay invariant across both verdicts)"
    )
    assert pass_meta.get("integrator_gate") is True, (
        f"D5 PASS cross-cut: `integrator_gate` discriminator literal True; "
        f"got {pass_meta.get('integrator_gate')!r}"
    )
    assert fail_meta.get("integrator_gate") is True, (
        f"D5 FAIL cross-cut: `integrator_gate` discriminator literal True "
        f"in FAIL branch; got {fail_meta.get('integrator_gate')!r}. Pins "
        "the metadata discriminator is identical across verdicts"
    )
