from __future__ import annotations

from typing import Any

_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "read": {
        "description": "Read a workspace file (outline mode for large non-target files).",
        "properties": {"path": {"type": "string"}, "mode": {"type": "string"}},
        "required": ["path"],
    },
    "write": {
        "description": "Write full file content within slice plan paths.",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    },
    "edit": {
        "description": "Replace old_text with new_text in a file.",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    },
    "grep": {
        "description": "Regex search within allowed paths.",
        "properties": {"pattern": {"type": "string"}, "paths": {"type": "array"}},
        "required": ["pattern", "paths"],
    },
    "shell": {
        "description": "Run allowlisted shell command.",
        "properties": {"command": {"type": "string"}, "args": {"type": "array"}},
        "required": ["command"],
    },
    "memory_fetch": {
        "description": "Fetch full memory chunk body by chunk id.",
        "properties": {"chunk_id": {"type": "string"}},
        "required": ["chunk_id"],
    },
}


class ToolSchemaResolver:
    def __init__(self) -> None:
        self._loaded: set[str] = set()

    def shorthand_list(self, tools: frozenset[str]) -> str:
        names = sorted(tools)
        return ", ".join(names) + " (schemas loaded on first use)"

    def schema_for(self, tool: str) -> dict[str, Any] | None:
        key = tool.strip().lower()
        self._loaded.add(key)
        return _TOOL_SCHEMAS.get(key)

    def loaded_tools(self) -> frozenset[str]:
        return frozenset(self._loaded)


_default_resolver = ToolSchemaResolver()


def default_tool_schema_resolver() -> ToolSchemaResolver:
    return _default_resolver
