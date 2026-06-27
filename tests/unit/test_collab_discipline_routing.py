from __future__ import annotations

from uuid import uuid4

from nimbusware_maker.chat_store_memory import InMemoryChatStore
from nimbusware_maker.collab_discipline_routing import maybe_route_collab_message
from nimbusware_auth.store import InMemoryCollabStore, InMemoryUserStore
from nimbusware_orchestrator.interjection_queue import queue_for_run
from nimbusware_store.memory import InMemoryEventStore


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
