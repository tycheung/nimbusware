from __future__ import annotations

from maker.chat.graph import (
    build_graph,
    child_turn_ids,
    leaf_descendants,
    path_to_root,
    sibling_count,
    turns_to_legacy_messages,
)
from maker.chat.memory import InMemoryChatStore
from maker.chat.postgres import PostgresChatStore

ChatStore = InMemoryChatStore | PostgresChatStore


def build_chat_store(database_url: str | None) -> ChatStore:
    if database_url:
        return PostgresChatStore(database_url)
    return InMemoryChatStore()


__all__ = [
    "ChatStore",
    "InMemoryChatStore",
    "PostgresChatStore",
    "build_chat_store",
    "build_graph",
    "child_turn_ids",
    "leaf_descendants",
    "path_to_root",
    "sibling_count",
    "turns_to_legacy_messages",
]
