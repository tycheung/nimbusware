from __future__ import annotations

from uuid import uuid4

from auth.store import InMemoryCollabStore, InMemoryUserStore
from maker.chat_store_memory import InMemoryChatStore
from maker.collab_discipline_routing import (
    append_routed_feedback_turns,
    maybe_route_collab_message,
)
from orchestrator.interjection_queue import queue_for_run
from store.memory import InMemoryEventStore


def test_maybe_route_collab_message_enqueues_taxonomy() -> None:
    user_store = InMemoryUserStore()
    collab_store = InMemoryCollabStore(user_store)
    chat_store = InMemoryChatStore()
    event_store = InMemoryEventStore()
    project_id = uuid4()
    session = chat_store.create_session(project_id=project_id)
    run_id = uuid4()
    chat_store.update_session(session.session_id, run_id=run_id)
    user = user_store.create_user(username="dev", password="secret", display_name="Dev")
    collab_store.add_participant(
        session_id=session.session_id,
        user_id=user.user_id,
        role="session_write",
        user_discipline="frontend",
    )
    routes = maybe_route_collab_message(
        event_store,
        chat_store,
        collab_store,
        session_id=session.session_id,
        message="@qa please verify",
        actor_user_id=user.user_id,
    )
    assert len(routes) == 1
    assert routes[0]["discipline"] == "qa"
    q = queue_for_run(str(run_id))
    assert q.items[0].taxonomy_key == "test_writer"
    assert "please verify" in q.items[0].message


def test_append_routed_feedback_turns_creates_thread_lines() -> None:
    user_store = InMemoryUserStore()
    collab_store = InMemoryCollabStore(user_store)
    chat_store = InMemoryChatStore()
    project_id = uuid4()
    session = chat_store.create_session(project_id=project_id)
    user = user_store.create_user(username="alice", password="secret", display_name="Alice")
    collab_store.add_participant(
        session_id=session.session_id,
        user_id=user.user_id,
        role="session_write",
        user_discipline="qa",
    )
    routes = [{"discipline": "qa", "taxonomy_key": "test_writer", "source": "mention"}]
    append_routed_feedback_turns(
        chat_store,
        collab_store,
        session_id=session.session_id,
        message="@qa verify",
        actor_user_id=user.user_id,
        routes=routes,
    )
    updated = chat_store.get_session(session.session_id)
    assert updated is not None
    turns = chat_store.list_turns(session.session_id)
    assert turns
    assert turns[-1].payload.get("kind") == "discipline_route"
    assert "Alice → test_writer" in turns[-1].text
