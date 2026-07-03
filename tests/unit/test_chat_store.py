from __future__ import annotations

from uuid import uuid4

import pytest

from maker.chat_store import InMemoryChatStore, build_graph, path_to_root


@pytest.fixture
def store() -> InMemoryChatStore:
    return InMemoryChatStore()


def test_session_append_and_active_path(store: InMemoryChatStore) -> None:
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    t1 = store.append_turn(session.session_id, role="user", text="fix bug")
    store.update_session(session.session_id, last_classification={"work_type": "patch"})
    t2 = store.append_turn(session.session_id, role="system", text="classified")
    path = store.get_active_path(session.session_id)
    assert [x.turn_id for x in path] == [t1.turn_id, t2.turn_id]
    assert path_to_root({x.turn_id: x for x in store.list_turns(session.session_id)}, t2.turn_id)


def test_fork_creates_sibling_branch(store: InMemoryChatStore) -> None:
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    root = store.append_turn(session.session_id, role="user", text="first prompt")
    store.append_turn(session.session_id, role="system", text="branch a")
    store.fork_at_turn(session.session_id, root.turn_id)
    sibling = store.append_turn(session.session_id, role="user", text="alternate prompt")
    graph = store.get_graph(session.session_id)
    assert len(graph["branches"]) >= 1
    kids = [n for n in graph["nodes"] if n["parent_turn_id"] == str(root.turn_id)]
    assert len(kids) == 2
    store.set_active_leaf(session.session_id, sibling.turn_id)
    path = store.get_active_path(session.session_id)
    assert path[-1].text == "alternate prompt"


def test_set_active_leaf_rejects_non_tip(store: InMemoryChatStore) -> None:
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    root = store.append_turn(session.session_id, role="user", text="parent")
    store.append_turn(session.session_id, role="system", text="child")
    with pytest.raises(ValueError, match="branch_tip"):
        store.set_active_leaf(session.session_id, root.turn_id)


def test_build_graph_marks_active_path(store: InMemoryChatStore) -> None:
    project_id = uuid4()
    session = store.create_session(project_id=project_id)
    store.append_turn(session.session_id, role="user", text="hello")
    session = store.get_session(session.session_id)
    assert session is not None
    graph = build_graph(session, {t.turn_id: t for t in store.list_turns(session.session_id)})
    assert any(n.get("is_active_path") for n in graph["nodes"])
