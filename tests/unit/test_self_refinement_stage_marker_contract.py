from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID

from agent_core.models import EventType
from nimbusware_extensions import SelfRefinementPolicy
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_self_refinement import SelfRefinementWorkflowBlock

if TYPE_CHECKING:
    from nimbusware_store.memory import InMemoryEventStore


_STAGE_STARTED = "stage.started"
_SR_STAGE = "self_refinement:policy"


def _sr_markers(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    """Return ``stage.started`` rows whose ``stage_name`` equals ``self_refinement:policy``."""
    return [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == _STAGE_STARTED
        and (r.get("payload") or {}).get("stage_name") == _SR_STAGE
    ]


def _sr_marker_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Extract ``metadata.self_refinement`` sub-dict (or empty dict) from a marker row."""
    meta = row.get("metadata") or {}
    inner = meta.get("self_refinement") or {}
    return inner if isinstance(inner, dict) else {}


def test_self_refinement_marker_policy_source_resolution_5_axis() -> None:
    """Pin policy-source resolution at pipeline.py:1451-1455 + workflow-block delegation.

    Coverage delta vs existing tests: today the orchestrator-side method has
    only HAPPY-path coverage (workflow_profile='self_refinement_on') which
    implicitly relies on the repo's policy.yaml existing. The False arm at
    line 1454-1455 (inline default `SelfRefinementPolicy(version=1, enabled=
    False, description="")`) has zero direct coverage.
    """
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    sentinel_pol_a1 = SelfRefinementPolicy(version=7, enabled=True, description="A1")
    with patch(
        "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
        return_value=sentinel_pol_a1,
    ) as loader_spy_a1:
        orch_a1._maybe_emit_self_refinement_stage_marker(rid_a1)  # noqa: SLF001
    assert loader_spy_a1.call_count == 1, (
        f"A1: load_self_refinement_policy called EXACTLY ONCE; got {loader_spy_a1.call_count}"
    )
    assert loader_spy_a1.call_args is not None, "A1: loader was invoked"
    loader_path_a1 = loader_spy_a1.call_args.args[0]
    assert (
        Path(loader_path_a1)
        .as_posix()
        .endswith(
            "configs/self_refinement/policy.yaml",
        )
    ), (
        f"A1: loader receives the policy.yaml path; got {loader_path_a1!r}. "
        "Pins the path-construction at pipeline.py:1451"
    )
    markers_a1 = _sr_markers(mem_a1, rid_a1)
    assert len(markers_a1) == 1, "A1: sentinel pol with enabled=True triggers emit"
    assert _sr_marker_metadata(markers_a1[0]).get("version") == 7, (
        "A1: sentinel pol.version=7 flows through to emitted metadata "
        "(confirms loader return is the pol source on the True arm)"
    )

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    wf_a2_on = SelfRefinementWorkflowBlock(enabled=True, version=None, description=None)
    with (
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=wf_a2_on,
        ),
        patch.object(Path, "is_file", return_value=False),
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
        ) as loader_spy_a2,
    ):
        orch_a2._maybe_emit_self_refinement_stage_marker(rid_a2)  # noqa: SLF001
    assert loader_spy_a2.call_count == 0, (
        f"A2: path.is_file()==False -> load_self_refinement_policy NOT called; "
        f"got {loader_spy_a2.call_count}. Pins the False-arm branch at "
        "pipeline.py:1454-1455 uses the inline default ONLY"
    )
    markers_a2 = _sr_markers(mem_a2, rid_a2)
    assert len(markers_a2) == 1, "A2: wf_sr enabled triggers emit on the False arm"
    assert _sr_marker_metadata(markers_a2[0]).get("version") == 1, (
        "A2: the inline default `SelfRefinementPolicy(version=1, ...)` is "
        "used when path.is_file() is False (no wf_sr.version override since "
        "wf_a2_on.version is None). Pins exact default version literal"
    )

    orch_a3, _ = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
        return_value=SelfRefinementWorkflowBlock(),
    ) as parser_spy_a3:
        orch_a3._maybe_emit_self_refinement_stage_marker(rid_a3)  # noqa: SLF001
    assert parser_spy_a3.call_count == 1, (
        f"A3: parse_self_refinement_workflow_block called EXACTLY ONCE; got "
        f"{parser_spy_a3.call_count}"
    )
    assert parser_spy_a3.call_args.args == (orch_a3._repo_root, "default"), (  # noqa: SLF001
        f"A3: parser receives (self._repo_root, wf_prof) POSITIONALLY; got "
        f"args={parser_spy_a3.call_args.args!r}. Pins positional routing "
        "(would break if refactored to kwarg)"
    )

    orch_a4, _ = make_dev_orchestrator()
    rid_a4_default = orch_a4.create_run("default")
    rid_a4_sr_on = orch_a4.create_run("self_refinement_on")
    with patch(
        "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
        return_value=SelfRefinementWorkflowBlock(),
    ) as parser_spy_a4:
        orch_a4._maybe_emit_self_refinement_stage_marker(rid_a4_default)  # noqa: SLF001
        orch_a4._maybe_emit_self_refinement_stage_marker(rid_a4_sr_on)  # noqa: SLF001
    assert parser_spy_a4.call_count == 2
    profiles_called = {c.args[1] for c in parser_spy_a4.call_args_list}
    assert profiles_called == {"default", "self_refinement_on"}, (
        f"A4: wf_prof derives PER-RUN from workflow_profile_from_run_created_rows; "
        f"two runs with different profiles on the same orchestrator yield two "
        f"distinct wf_prof args. Got profiles_called={profiles_called!r}. Pins "
        "per-run profile lookup (would break if cached on orchestrator state)"
    )

    orch_a5, _ = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    with patch.object(
        orch_a5._store,  # noqa: SLF001
        "list_run_events",
        wraps=orch_a5._store.list_run_events,  # noqa: SLF001
    ) as list_spy_a5:
        orch_a5._maybe_emit_self_refinement_stage_marker(rid_a5)  # noqa: SLF001
    assert list_spy_a5.call_count == 1, (
        f"A5: list_run_events called EXACTLY ONCE per invocation; got "
        f"{list_spy_a5.call_count}. Pins no rows-refresh seam (distinct from "
        "fo103 Part D's in-loop refresh on the critique-fail-findings helper)"
    )


def test_self_refinement_marker_or_enable_early_return_5_axis() -> None:
    """Pin `not pol.enabled and not wf_sr.enabled` early return at pipeline.py:1457-1458.

    Coverage delta vs existing tests: today only single-source coverage exists
    (workflow ON -> emit, default -> no emit). The OR semantics across pol and
    wf_sr is unpinned; a refactor flipping to AND or double-emit would not be
    caught by today's tests.
    """
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=False, description=""),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=False),
        ),
    ):
        orch_b1._maybe_emit_self_refinement_stage_marker(rid_b1)  # noqa: SLF001
    assert _sr_markers(mem_b1, rid_b1) == [], (
        "B1: both pol.enabled=False AND wf_sr.enabled=False -> no emit "
        "(pins the AND-of-negations short-circuit)"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=2, enabled=True, description="pol_b2"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=False),
        ),
    ):
        orch_b2._maybe_emit_self_refinement_stage_marker(rid_b2)  # noqa: SLF001
    assert len(_sr_markers(mem_b2, rid_b2)) == 1, (
        "B2: pol.enabled=True alone triggers emit (wf_sr.enabled=False does "
        "NOT block). Pins OR semantics on the pol side"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=False, description=""),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=True, version=3, description="wf_b3"),
        ),
    ):
        orch_b3._maybe_emit_self_refinement_stage_marker(rid_b3)  # noqa: SLF001
    assert len(_sr_markers(mem_b3, rid_b3)) == 1, (
        "B3: wf_sr.enabled=True alone triggers emit (pol.enabled=False does "
        "NOT block). Pins OR semantics on the wf_sr side"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=2, enabled=True, description="pol_b4"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=True, version=5, description="wf_b4"),
        ),
    ):
        orch_b4._maybe_emit_self_refinement_stage_marker(rid_b4)  # noqa: SLF001
    assert len(_sr_markers(mem_b4, rid_b4)) == 1, (
        "B4: both pol AND wf_sr enabled -> EXACTLY ONE emit (not double). "
        "Pins OR semantics (would break if refactored to a double-emit pattern)"
    )

    orch_b5, mem_b5 = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    with patch(
        "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
        return_value=SelfRefinementWorkflowBlock(),
    ):
        orch_b5._maybe_emit_self_refinement_stage_marker(rid_b5)  # noqa: SLF001
    assert _sr_markers(mem_b5, rid_b5) == [], (
        "B5: bare-default `SelfRefinementWorkflowBlock()` (enabled=False, "
        "version=None, description=None) + repo's `policy.yaml` (enabled=False) "
        "-> no emit. Pins the bare-default block both-off path"
    )


def test_self_refinement_marker_override_semantics_5_axis() -> None:
    """Pin version + description override at pipeline.py:1460-1465.

    Coverage delta vs existing tests: today's `test_emit_self_refinement_marker
    _when_workflow_enables` verifies `metadata.version == 1` but does NOT
    distinguish whether the value came from pol or wf_sr (the repo's policy
    has version=1 AND `self_refinement_on` has version=1, so both sources
    produce the same observable value). fo105 C pins the override DIRECTION
    explicitly so a future swap (pol beats wf_sr) would fail loudly.
    """
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=3, enabled=True, description="from_pol"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=False, version=None, description=None),
        ),
    ):
        orch_c1._maybe_emit_self_refinement_stage_marker(rid_c1)  # noqa: SLF001
    markers_c1 = _sr_markers(mem_c1, rid_c1)
    assert len(markers_c1) == 1
    assert _sr_marker_metadata(markers_c1[0]).get("version") == 3, (
        "C1: wf_sr.version=None preserves pol.version=3 (no override "
        "fires; `if wf_sr.version is not None` evaluates False)"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=3, enabled=True, description="from_pol"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=False, version=5, description=None),
        ),
    ):
        orch_c2._maybe_emit_self_refinement_stage_marker(rid_c2)  # noqa: SLF001
    markers_c2 = _sr_markers(mem_c2, rid_c2)
    assert len(markers_c2) == 1
    assert _sr_marker_metadata(markers_c2[0]).get("version") == 5, (
        "C2: wf_sr.version=5 overrides pol.version=3 (wf_sr beats pol). "
        "Pins override DIRECTION -- would silently flip if refactored to "
        "`pol beats wf_sr` semantics"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=True, description="pol_desc"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(enabled=False, version=None, description=None),
        ),
    ):
        orch_c3._maybe_emit_self_refinement_stage_marker(rid_c3)  # noqa: SLF001
    markers_c3 = _sr_markers(mem_c3, rid_c3)
    assert _sr_marker_metadata(markers_c3[0]).get("description") == "pol_desc", (
        "C3: wf_sr.description=None preserves pol.description='pol_desc' "
        "(no override fires; `if wf_sr.description is not None` False)"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=True, description="pol_default"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(
                enabled=False,
                version=None,
                description="wf_custom",
            ),
        ),
    ):
        orch_c4._maybe_emit_self_refinement_stage_marker(rid_c4)  # noqa: SLF001
    markers_c4 = _sr_markers(mem_c4, rid_c4)
    assert _sr_marker_metadata(markers_c4[0]).get("description") == "wf_custom", (
        "C4: wf_sr.description='wf_custom' overrides pol.description="
        "'pol_default'. Pins override DIRECTION (parallel to C2 for version)"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=True, description="pol_desc"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(
                enabled=False,
                version=99,
                description="wf_desc",
            ),
        ),
    ):
        orch_c5._maybe_emit_self_refinement_stage_marker(rid_c5)  # noqa: SLF001
    meta_c5 = _sr_marker_metadata(_sr_markers(mem_c5, rid_c5)[0])
    assert meta_c5.get("version") == 99 and meta_c5.get("description") == "wf_desc", (
        f"C5: both overrides set simultaneously -- version=99 AND "
        f"description='wf_desc' BOTH flow through. Got meta={meta_c5!r}. "
        "Pins INDEPENDENT override application (no coupling between the two "
        "`if not None` arms; a refactor that gated one on the other would "
        "fail here)"
    )


def test_self_refinement_marker_emit_shape_bounding_no_dedup_5_axis() -> None:
    """Pin emit shape + literal stage_name + attempt + metadata + [:2000] + NO-dedup.

    Coverage delta vs existing tests: today's `test_emit_self_refinement_marker
    _when_workflow_enables` spot-checks `version` and `description isinstance
    str` but does NOT pin (a) the literal `stage_name` value, (b) `attempt==1`,
    (c) the metadata envelope key `self_refinement`, (d) the `[:2000]`
    bounding, or (e) the NO-dedup STRUCTURAL DIVERGENCE from fo102 / fo104
    escalation emitters.
    """
    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=42, enabled=True, description="meta_desc"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(
                enabled=False,
                version=None,
                description=None,
            ),
        ),
    ):
        orch_d1._maybe_emit_self_refinement_stage_marker(rid_d1)  # noqa: SLF001
    markers_d1 = _sr_markers(mem_d1, rid_d1)
    assert len(markers_d1) == 1
    payload_d1 = markers_d1[0].get("payload") or {}
    assert payload_d1.get("stage_name") == _SR_STAGE, (
        f"D1: payload.stage_name literal == '{_SR_STAGE}'; got "
        f"{payload_d1.get('stage_name')!r}. Would silently break under a "
        "refactor renaming to e.g. `self_refinement.policy` or `self-refinement:policy`"
    )

    assert payload_d1.get("attempt") == 1, (
        f"D2: payload.attempt == 1 on first marker; got {payload_d1.get('attempt')!r}."
    )

    metadata_d1 = markers_d1[0].get("metadata") or {}
    sr_meta = metadata_d1.get("self_refinement") or {}
    assert sr_meta.get("version") == 42
    assert sr_meta.get("description") == "meta_desc"
    assert isinstance(sr_meta.get("evaluation"), dict)
    assert sr_meta.get("max_iterations") == 3

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    long_desc = "X" * 3000
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=True, description=long_desc),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(
                enabled=False,
                version=None,
                description=None,
            ),
        ),
    ):
        orch_d4._maybe_emit_self_refinement_stage_marker(rid_d4)  # noqa: SLF001
    bounded_desc = _sr_marker_metadata(_sr_markers(mem_d4, rid_d4)[0]).get("description")
    assert isinstance(bounded_desc, str)
    assert len(bounded_desc) == 2000, (
        f"D4: long description bounded to EXACTLY 2000 chars; got len="
        f"{len(bounded_desc)}. Pins the `[:2000]` slice (would fail loudly if "
        "refactored to `[:2048]`, `[:4096]`, or removed)"
    )
    assert bounded_desc == "X" * 2000, (
        "D4: bounded description preserves leading chars verbatim (slice "
        "semantics, not e.g. truncation with ellipsis or hash)"
    )

    orch_d5, mem_d5 = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    with (
        patch(
            "nimbusware_orchestrator.pipeline.load_self_refinement_policy",
            return_value=SelfRefinementPolicy(version=1, enabled=True, description="d5"),
        ),
        patch(
            "nimbusware_orchestrator.pipeline.parse_self_refinement_workflow_block",
            return_value=SelfRefinementWorkflowBlock(
                enabled=False,
                version=None,
                description=None,
            ),
        ),
    ):
        orch_d5._maybe_emit_self_refinement_stage_marker(rid_d5)  # noqa: SLF001
        orch_d5._maybe_emit_self_refinement_stage_marker(rid_d5)  # noqa: SLF001
    assert len(_sr_markers(mem_d5, rid_d5)) == 2, (
        f"D5: NO dedup -- calling the helper TWICE on the same run emits "
        f"TWO rows; got {len(_sr_markers(mem_d5, rid_d5))}. KEY STRUCTURAL "
        "DIVERGENCE from fo102 / fo104 escalation emitters (which all dedup "
        "by reason_code). A future 'unify all emitters with dedup' refactor "
        "would silently break consumers relying on repeated "
        f"'{_SR_STAGE}' markers (e.g., per-attempt iteration tracking)"
    )
    attempts = [(m.get("payload") or {}).get("attempt") for m in _sr_markers(mem_d5, rid_d5)]
    assert attempts == [1, 2], f"D5: attempt counter increments; got {attempts!r}"
    assert EventType.STAGE_STARTED.value == _STAGE_STARTED, (
        "D5 sanity: EventType.STAGE_STARTED string value matches local constant"
    )
