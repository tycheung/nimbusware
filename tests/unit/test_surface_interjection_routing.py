from __future__ import annotations

from uuid import uuid4

from orchestrator.interjection_queue import queue_for_run
from orchestrator.micro_slice import SlicePlan
from orchestrator.slice_interjection import (
    InterjectionCycle,
    apply_surface_steer_to_plan,
    process_interjection_cycle,
    steer_excerpt_from_cycle,
)
from orchestrator.surface_interjection_routing import (
    enqueue_surface_steers,
    surface_steer_routes,
)
from store.memory import InMemoryEventStore


def test_surface_steer_routes_from_mention() -> None:
    routes = surface_steer_routes("@web fix the login button")
    assert len(routes) == 1
    assert routes[0]["surface_id"] == "web"


def test_enqueue_surface_steers_sets_surface_id() -> None:
    run_id = uuid4()
    store = InMemoryEventStore()
    routes = enqueue_surface_steers(
        store,
        run_id=run_id,
        message="@api add health endpoint",
    )
    assert routes[0]["surface_id"] == "api"
    q = queue_for_run(str(run_id))
    assert q.items[0].surface_id == "api"
    assert q.items[0].steer_from_chat is True


def test_apply_surface_steer_to_plan() -> None:
    plan = SlicePlan("s1", ("a.py",), "base", acceptance_criteria="ok", surface_id="web")
    item = queue_for_run("r").enqueue(
        "[steer:api] focus on backend",
        steer_from_chat=True,
        surface_id="api",
    )
    cycle = InterjectionCycle(items=[item], steer_from_chat=True)
    updated = apply_surface_steer_to_plan(
        plan,
        cycle,
        manifest={"stacks": {"api": "fastapi_python"}},
    )
    assert updated.surface_id == "api"
    assert updated.stack_id == "fastapi_python"
    assert "Surface steer" in updated.rationale


def test_steer_excerpt_includes_surface_tag() -> None:
    run_id = str(uuid4())
    store = InMemoryEventStore()
    q = queue_for_run(run_id)
    q.enqueue("[steer:web] polish header")
    cycle = process_interjection_cycle(store, run_id)
    excerpt = steer_excerpt_from_cycle(cycle)
    assert "[web]" in excerpt
    assert "polish header" in excerpt
