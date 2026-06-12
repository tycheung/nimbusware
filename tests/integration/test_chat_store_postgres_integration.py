from __future__ import annotations

import os
from uuid import uuid4

import pytest

from nimbusware_maker.chat_store import PostgresChatStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_postgres_chat_analytics_turn_rows() -> None:
    store = PostgresChatStore(_url())
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    store.append_turn(session.session_id, role="user", text="hello postgres")
    run_id = uuid4()
    store.append_turn(
        session.session_id,
        role="run_status",
        text="started patch",
        work_type="patch",
        work_type_source="classifier",
        run_id=run_id,
    )
    rows = store.list_recent_analytics_turn_rows(limit_sessions=20)
    assert any(str(r.get("session_id")) == str(session.session_id) for r in rows)
    assert any(r.get("work_type_source") == "classifier" for r in rows)
