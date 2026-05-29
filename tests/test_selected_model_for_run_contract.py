"""``_selected_model_for_run`` direct contract.

fo92's Next-slice item (5) flagged "next-sharpest gap from agent exploration".
Audit of [`pipeline.py:561-573`](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
surfaced this single-method gap: ``_selected_model_for_run`` reverse-walks the
event store looking for ``MODEL_SELECTED_PRIMARY`` (reads ``model_id``) or
``MODEL_SELECTED_FALLBACK`` (reads ``selected_model_id``) and returns the
first hit whose value is a string.

Coverage today: ``MODEL_SELECTED_PRIMARY`` happy-path is indirectly covered
via fo91's ``_append_model_selected_primary`` helper in
[`tests/test_optional_critique_emitters_contract.py`](d:\\Hermes\\tests\\test_optional_critique_emitters_contract.py)
Parts C/D model-id propagation. ``MODEL_SELECTED_FALLBACK`` has **zero**
direct test coverage anywhere. Reverse-walk precedence, ``isinstance``
type-guard skip-and-continue, field-name asymmetry (``model_id`` vs
``selected_model_id``), and multi-run isolation are all unpinned.

This is foundational -- ``_selected_model_for_run`` feeds every LLM call
site (``_emit_test_writer_critique_optional``,
``_emit_planner_critique_optional``, plus the inline impl-critique LLM call
at ``pipeline.py:1188-1204``).

fo93 closes the gap via 4 parts spanning 16 axes (~18 assertions, source
unchanged):

* **Part A** -- per-event-type happy-path field reads (4 axes -- empty store
 / single PRIMARY / single FALLBACK / PRIMARY + unrelated event).
* **Part B** -- reverse-walk LAST-wins precedence (4 axes -- 2 PRIMARY / 2
 FALLBACK / PRIMARY-then-FALLBACK / FALLBACK-then-PRIMARY).
* **Part C** -- ``isinstance(mid, str)`` type-guard skip-and-continue (4 axes
 -- non-string PRIMARY / non-string FALLBACK / valid earlier FALLBACK falls
 through non-string PRIMARY / mirror).
* **Part D** -- cross-cutting negative axes (4 axes -- multi-run isolation /
 missing PRIMARY field / missing FALLBACK field / unknown event_type).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    ModelSelectedFallbackEvent,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
    RunStartedEvent,
    RunStartedPayload,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


def _append_primary(
    mem: InMemoryEventStore,
    rid: UUID,
    model_id: str = "llama3.1:8b",
) -> None:
    """Append a synthetic ``MODEL_SELECTED_PRIMARY`` row (mirrors fo91 helper)."""
    mem.append(
        ModelSelectedPrimaryEvent(
            event_type=EventType.MODEL_SELECTED_PRIMARY,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelSelectedPrimaryPayload(
                provider="ollama",
                model_id=model_id,
            ),
        ),
    )


def _append_fallback(
    mem: InMemoryEventStore,
    rid: UUID,
    selected_model_id: str = "fallback-7b",
) -> None:
    """Append a synthetic ``MODEL_SELECTED_FALLBACK`` row.

    ``ModelSelectedFallbackPayload`` requires 4 fields
    (``provider`` / ``selected_model_id`` / ``reason_code`` /
    ``original_model_id``); we default the non-test-relevant ones so
    call-sites stay compact.
    """
    mem.append(
        ModelSelectedFallbackEvent(
            event_type=EventType.MODEL_SELECTED_FALLBACK,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelSelectedFallbackPayload(
                provider="ollama",
                selected_model_id=selected_model_id,
                reason_code="primary_unavailable",
                original_model_id="llama3.1:8b",
            ),
        ),
    )


def _append_run_started(mem: InMemoryEventStore, rid: UUID) -> None:
    """Append a synthetic ``RUN_STARTED`` row (used as an unrelated interleaved event)."""
    mem.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="fo93-test"),
        ),
    )


def test_selected_model_for_run_per_event_type_happy_path_4_axis() -> None:
    """Pin per-event-type happy-path field reads.

    A1 -- empty store -> ``None``.
    A2 -- single PRIMARY -> reads ``payload.model_id``.
    A3 -- single FALLBACK -> reads ``payload.selected_model_id`` (NOT model_id).
    A4 -- PRIMARY + interleaved RUN_STARTED -> non-model row ignored.
    """
    orch_a1, _ = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    assert orch_a1._selected_model_for_run(rid_a1) is None, (  # noqa: SLF001
        "A1: empty store (no model events) must return None"
    )

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    _append_primary(mem_a2, rid_a2, model_id="primary-13b")
    assert orch_a2._selected_model_for_run(rid_a2) == "primary-13b", (  # noqa: SLF001
        "A2: single PRIMARY must read payload.model_id"
    )

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    _append_fallback(mem_a3, rid_a3, selected_model_id="fallback-7b")
    assert orch_a3._selected_model_for_run(rid_a3) == "fallback-7b", (  # noqa: SLF001
        "A3: single FALLBACK must read payload.selected_model_id (NOT model_id)"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    _append_primary(mem_a4, rid_a4, model_id="primary-13b")
    _append_run_started(mem_a4, rid_a4)
    assert orch_a4._selected_model_for_run(rid_a4) == "primary-13b", (  # noqa: SLF001
        "A4: interleaved RUN_STARTED (most recent row) must be ignored by event_type filter"
    )


def test_selected_model_for_run_reverse_walk_last_wins_precedence_4_axis() -> None:
    """Pin the reverse-iteration LAST-wins contract.

    B1 -- two PRIMARY rows: latter wins.
    B2 -- two FALLBACK rows: latter wins.
    B3 -- PRIMARY then FALLBACK: FALLBACK wins (most recent).
    B4 -- FALLBACK then PRIMARY: PRIMARY wins (most recent).
    """
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    _append_primary(mem_b1, rid_b1, model_id="primary-A")
    _append_primary(mem_b1, rid_b1, model_id="primary-B")
    assert orch_b1._selected_model_for_run(rid_b1) == "primary-B", (  # noqa: SLF001
        "B1: two PRIMARY rows -- latter wins under reverse-walk"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    _append_fallback(mem_b2, rid_b2, selected_model_id="fallback-X")
    _append_fallback(mem_b2, rid_b2, selected_model_id="fallback-Y")
    assert orch_b2._selected_model_for_run(rid_b2) == "fallback-Y", (  # noqa: SLF001
        "B2: two FALLBACK rows -- latter wins under reverse-walk"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    _append_primary(mem_b3, rid_b3, model_id="primary-first")
    _append_fallback(mem_b3, rid_b3, selected_model_id="fallback-latest")
    assert orch_b3._selected_model_for_run(rid_b3) == "fallback-latest", (  # noqa: SLF001
        "B3: PRIMARY then FALLBACK -- FALLBACK wins as the most recent row"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    _append_fallback(mem_b4, rid_b4, selected_model_id="fallback-first")
    _append_primary(mem_b4, rid_b4, model_id="primary-latest")
    assert orch_b4._selected_model_for_run(rid_b4) == "primary-latest", (  # noqa: SLF001
        "B4: FALLBACK then PRIMARY -- PRIMARY wins as the most recent row "
        "(proves both event types participate equally in reverse-walk)"
    )


def test_selected_model_for_run_isinstance_type_guard_skip_and_continue_4_axis() -> None:
    """Pin the ``isinstance(mid, str)`` skip-and-continue contract.

    Each axis post-mutates ``mem._rows[-1]["payload"][<field>]`` to bypass
    Pydantic's ``str`` enforcement, mirroring fo92 Part D5's technique.

    C1 -- PRIMARY mutated ``model_id=None`` -> ``None``.
    C2 -- FALLBACK mutated ``selected_model_id=42`` -> ``None``.
    C3 -- valid FALLBACK earlier + non-string PRIMARY later: falls
    through to FALLBACK (proves loop continues, NOT early-return None).
    C4 -- valid PRIMARY earlier + non-string FALLBACK later: mirror.
    """
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    _append_primary(mem_c1, rid_c1, model_id="primary-13b")
    mem_c1._rows[-1]["payload"]["model_id"] = None  # noqa: SLF001
    assert orch_c1._selected_model_for_run(rid_c1) is None, (  # noqa: SLF001
        "C1: PRIMARY with non-string model_id must be skipped by isinstance guard"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    _append_fallback(mem_c2, rid_c2, selected_model_id="fallback-7b")
    mem_c2._rows[-1]["payload"]["selected_model_id"] = 42  # noqa: SLF001
    assert orch_c2._selected_model_for_run(rid_c2) is None, (  # noqa: SLF001
        "C2: FALLBACK with non-string selected_model_id must be skipped"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    _append_fallback(mem_c3, rid_c3, selected_model_id="valid-fallback")
    _append_primary(mem_c3, rid_c3, model_id="primary-bad")
    mem_c3._rows[-1]["payload"]["model_id"] = None  # noqa: SLF001
    assert orch_c3._selected_model_for_run(rid_c3) == "valid-fallback", (  # noqa: SLF001
        "C3: non-string PRIMARY (latest) must be skipped and loop must continue "
        "to earlier valid FALLBACK"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    _append_primary(mem_c4, rid_c4, model_id="valid-primary")
    _append_fallback(mem_c4, rid_c4, selected_model_id="fallback-bad")
    mem_c4._rows[-1]["payload"]["selected_model_id"] = None  # noqa: SLF001
    assert orch_c4._selected_model_for_run(rid_c4) == "valid-primary", (  # noqa: SLF001
        "C4: non-string FALLBACK (latest) must be skipped and loop must continue "
        "to earlier valid PRIMARY"
    )


def test_selected_model_for_run_cross_cutting_negative_axes_4_axis() -> None:
    """Pin cross-cutting negative + isolation axes.

    D1 -- multi-run isolation: two runs in same store; PRIMARY for run_a
    only -> run_a returns model_id; run_b returns ``None``.
    D2 -- PRIMARY with missing ``model_id`` field -> ``None``.
    D3 -- FALLBACK with missing ``selected_model_id`` field -> ``None``.
    D4 -- unknown event_type -> ``None`` (both ``et == ...`` guards reject).
    """
    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1_a = orch_d1.create_run("default")
    rid_d1_b = orch_d1.create_run("default")
    _append_primary(mem_d1, rid_d1_a, model_id="primary-for-a")
    assert orch_d1._selected_model_for_run(rid_d1_a) == "primary-for-a", (  # noqa: SLF001
        "D1: run_a with PRIMARY must return its model_id"
    )
    assert orch_d1._selected_model_for_run(rid_d1_b) is None, (  # noqa: SLF001
        "D1: run_b (no model events) must return None despite sharing the store with run_a"
    )

    orch_d2, mem_d2 = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    _append_primary(mem_d2, rid_d2, model_id="primary-13b")
    mem_d2._rows[-1]["payload"].pop("model_id")  # noqa: SLF001
    assert orch_d2._selected_model_for_run(rid_d2) is None, (  # noqa: SLF001
        "D2: PRIMARY with missing model_id field must return None "
        "(pl.get('model_id') returns None which fails isinstance(_, str))"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    _append_fallback(mem_d3, rid_d3, selected_model_id="fallback-7b")
    mem_d3._rows[-1]["payload"].pop("selected_model_id")  # noqa: SLF001
    assert orch_d3._selected_model_for_run(rid_d3) is None, (  # noqa: SLF001
        "D3: FALLBACK with missing selected_model_id field must return None"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    _append_primary(mem_d4, rid_d4, model_id="primary-13b")
    mem_d4._rows[-1]["event_type"] = "model.selected.unknown"  # noqa: SLF001
    assert orch_d4._selected_model_for_run(rid_d4) is None, (  # noqa: SLF001
        "D4: unknown event_type must be rejected by both event_type guards"
    )
