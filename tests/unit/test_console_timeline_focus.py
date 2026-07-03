from __future__ import annotations

from console.run_list_pagination_display.timeline_events import (
    timeline_events_near_store_seq,
    timeline_events_table_rows,
)


def test_timeline_events_near_store_seq_window() -> None:
    events = [{"store_seq": i, "event_type": "x"} for i in range(1, 11)]
    near = timeline_events_near_store_seq(events, 5, window=2)
    assert [e["store_seq"] for e in near] == [3, 4, 5, 6, 7]


def test_timeline_events_table_rows_includes_store_seq() -> None:
    rows = timeline_events_table_rows([{"store_seq": 42, "event_type": "run.created"}])
    assert rows[0]["store_seq"] == "42"
