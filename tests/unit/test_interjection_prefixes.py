from __future__ import annotations

from uuid import uuid4

from nimbusware_orchestrator.interjection_queue import (
    InterjectionPriority,
    parse_interjection_prefix,
    queue_for_run,
)
from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.slice_interjection import (
    apply_interjection_to_plan,
    gate_result_for_skip_slice,
    handle_patch_from_chat_interjection,
    process_interjection_cycle,
    steer_excerpt_from_cycle,
)
from nimbusware_store.memory import InMemoryEventStore


def test_parse_interjection_prefixes() -> None:
    msg, flags, surface = parse_interjection_prefix("[patch] fix auth test")
    assert msg == "fix auth test"
    assert flags["patch_from_chat"] is True
    assert surface is None

    msg2, flags2, surface2 = parse_interjection_prefix("[steer] prefer smaller diff")
    assert msg2 == "prefer smaller diff"
    assert flags2["steer_from_chat"] is True
    assert surface2 is None

    msg3, flags3, surface3 = parse_interjection_prefix("[skip] defer this slice")
    assert msg3 == "defer this slice"
    assert flags3["skip_slice"] is True
    assert surface3 is None

    msg4, flags4, surface4 = parse_interjection_prefix("[steer:web] tighten login flow")
    assert msg4 == "tighten login flow"
    assert flags4["steer_from_chat"] is True
    assert surface4 == "web"


def test_enqueue_sets_prefix_flags() -> None:
    run_id = str(uuid4())
    q = queue_for_run(run_id)
    item = q.enqueue("[patch] hotfix login", priority=InterjectionPriority.NEXT)
    assert item.patch_from_chat is True
    assert item.message == "hotfix login"
    assert not item.build_from_chat

    steer = q.enqueue("[steer] use pathlib", priority=InterjectionPriority.LAST)
    assert steer.steer_from_chat is True
    assert steer.message == "use pathlib"

    surface_steer = q.enqueue("[steer:api] add pagination", priority=InterjectionPriority.NEXT)
    assert surface_steer.steer_from_chat is True
    assert surface_steer.surface_id == "api"
    assert surface_steer.message == "add pagination"


def test_process_interjection_cycle_aggregates_flags() -> None:
    run_id = str(uuid4())
    store = InMemoryEventStore()
    q = queue_for_run(run_id)
    q.enqueue("[steer] tighten scope")
    q.enqueue("[patch] fix failing test")
    cycle = process_interjection_cycle(store, run_id)
    assert cycle.patch_from_chat is True
    assert cycle.steer_from_chat is True
    assert steer_excerpt_from_cycle(cycle) == "tighten scope"


def test_apply_interjection_excludes_prefixed_messages() -> None:
    run_id = str(uuid4())
    store = InMemoryEventStore()
    q = queue_for_run(run_id)
    q.enqueue("plain note")
    q.enqueue("[steer] agent only")
    cycle = process_interjection_cycle(store, run_id)
    plan = SlicePlan("s1", ("a.py",), "base", ("ok",))
    updated = apply_interjection_to_plan(plan, cycle)
    assert "plain note" in updated.rationale
    assert "agent only" not in updated.rationale


def test_patch_from_chat_inserts_backlog_slice() -> None:
    from agent_core.models.backlog import (
        BacklogEpic,
        BacklogFeature,
        BacklogSlice,
        DeliveryBacklog,
    )
    from nimbusware_orchestrator.backlog_generator import emit_backlog_generated

    run_id = uuid4()
    store = InMemoryEventStore()
    backlog = DeliveryBacklog(
        campaign_id=str(run_id),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="Epic",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="Feature",
                        slices=(
                            BacklogSlice(
                                slice_id="existing", rationale="old", target_paths=("a.py",)
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    emit_backlog_generated(store, run_id, backlog, generator_mode="stub")
    rows = store.list_run_events(str(run_id))

    q = queue_for_run(str(run_id))
    q.enqueue("[patch] fix tests/test_auth.py")
    cycle = process_interjection_cycle(store, run_id)
    slice_id = handle_patch_from_chat_interjection(store, run_id, cycle, rows)
    assert slice_id
    assert slice_id.startswith("patch-")

    revised_rows = store.list_run_events(str(run_id))
    revised = [r for r in revised_rows if r.get("event_type") == "delivery_backlog.revised"]
    assert revised
    patch_events = [
        r
        for r in revised_rows
        if (r.get("payload") or {}).get("stage_name") == "interjection.patch_from_chat"
    ]
    assert patch_events


def test_skip_slice_gate_passes() -> None:
    plan = SlicePlan("s-skip", ("a.py",), "r", ("ok",))
    gate = gate_result_for_skip_slice(plan)
    assert gate.passed is True
    assert gate.status == "skipped_by_operator"
