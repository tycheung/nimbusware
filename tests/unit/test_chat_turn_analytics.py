from __future__ import annotations

from uuid import uuid4

from maker.chat.memory import InMemoryChatStore
from projections.builders.chat_turn_analytics import build_chat_turn_summary


def test_chat_turn_summary_classifier_rate() -> None:
    store = InMemoryChatStore()
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    store.append_turn(session.session_id, role="user", text="fix test")
    store.append_turn(
        session.session_id,
        role="run_status",
        text="started",
        work_type="patch",
        work_type_source="classifier",
        run_id=uuid4(),
    )
    store.append_turn(
        session.session_id,
        role="run_status",
        text="override",
        work_type="slice",
        work_type_source="operator_override",
        run_id=uuid4(),
    )
    rows = store.list_recent_analytics_turn_rows(limit_sessions=10)
    body = build_chat_turn_summary(rows, limit_sessions=10)
    assert body["turn_count"] == 3
    assert body["classifier_start_count"] == 1
    assert body["override_start_count"] == 1
    assert body["classifier_acceptance_rate"] == 0.5
    assert body["sessions_with_run_id"] == 1


def test_chat_turn_summary_empty() -> None:
    body = build_chat_turn_summary([], limit_sessions=50)
    assert body["sessions_scanned"] == 0
    assert body["classifier_acceptance_rate"] is None
