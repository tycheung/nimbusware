from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

_PREFIX_FLAGS: tuple[tuple[str, str], ...] = (
    ("[build]", "build_from_chat"),
    ("[patch]", "patch_from_chat"),
    ("[steer]", "steer_from_chat"),
    ("[skip]", "skip_slice"),
)


class InterjectionPriority(str, Enum):
    NEXT = "next"
    LAST = "last"


@dataclass
class InterjectionItem:
    item_id: str
    message: str
    priority: InterjectionPriority
    force_break: bool = False
    build_from_chat: bool = False
    patch_from_chat: bool = False
    steer_from_chat: bool = False
    skip_slice: bool = False
    discipline: str | None = None
    taxonomy_key: str | None = None
    surface_id: str | None = None
    routed_from_user_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class InterjectionQueue:
    items: list[InterjectionItem] = field(default_factory=list)

    def enqueue(
        self,
        message: str,
        *,
        priority: InterjectionPriority = InterjectionPriority.NEXT,
        force_break: bool = False,
        build_from_chat: bool = False,
        patch_from_chat: bool = False,
        steer_from_chat: bool = False,
        skip_slice: bool = False,
        discipline: str | None = None,
        taxonomy_key: str | None = None,
        surface_id: str | None = None,
        routed_from_user_id: str | None = None,
    ) -> InterjectionItem:
        stripped, prefix_flags, prefix_surface = parse_interjection_prefix(message)
        item = InterjectionItem(
            item_id=str(uuid4()),
            message=stripped,
            priority=priority,
            force_break=force_break,
            build_from_chat=build_from_chat or prefix_flags.get("build_from_chat", False),
            patch_from_chat=patch_from_chat or prefix_flags.get("patch_from_chat", False),
            steer_from_chat=steer_from_chat or prefix_flags.get("steer_from_chat", False),
            skip_slice=skip_slice or prefix_flags.get("skip_slice", False),
            discipline=discipline,
            taxonomy_key=taxonomy_key,
            surface_id=surface_id or prefix_surface,
            routed_from_user_id=routed_from_user_id,
        )
        if priority == InterjectionPriority.LAST:
            self.items.append(item)
        else:
            self.items.insert(0, item)
        return item

    def drain(self) -> list[InterjectionItem]:
        ordered = sorted(
            self.items,
            key=lambda i: (0 if i.priority == InterjectionPriority.NEXT else 1, i.created_at),
        )
        self.items.clear()
        return ordered

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": len(self.items),
            "items": [
                {
                    "item_id": i.item_id,
                    "message": i.message,
                    "priority": i.priority.value,
                    "force_break": i.force_break,
                    "build_from_chat": i.build_from_chat,
                    "patch_from_chat": i.patch_from_chat,
                    "steer_from_chat": i.steer_from_chat,
                    "skip_slice": i.skip_slice,
                    "discipline": i.discipline,
                    "taxonomy_key": i.taxonomy_key,
                    "surface_id": i.surface_id,
                    "routed_from_user_id": i.routed_from_user_id,
                }
                for i in self.items
            ],
        }


_RUN_QUEUES: dict[str, InterjectionQueue] = {}


_STEER_SURFACE_PREFIX_RE = re.compile(r"^\[steer:([a-z]+)\]\s*", re.I)
_SURFACE_ALIASES = {
    "web": "web",
    "frontend": "web",
    "ui": "web",
    "api": "api",
    "contract": "contract",
    "openapi": "contract",
    "infra": "infra",
}


def _normalize_surface_id(raw: str) -> str | None:
    key = str(raw or "").strip().lower().lstrip("@")
    return _SURFACE_ALIASES.get(key) if key else None


def _parse_surface_steer_prefix(message: str) -> tuple[str, str | None]:
    stripped = message.strip()
    match = _STEER_SURFACE_PREFIX_RE.match(stripped)
    if not match:
        return stripped, None
    surface_id = _normalize_surface_id(match.group(1))
    return stripped[match.end() :].strip(), surface_id


def parse_interjection_prefix(message: str) -> tuple[str, dict[str, bool], str | None]:
    stripped = message.strip()
    flags: dict[str, bool] = {}
    surface_id: str | None = None
    steer_body, steer_surface = _parse_surface_steer_prefix(stripped)
    if steer_surface:
        return steer_body, {"steer_from_chat": True}, steer_surface
    low = stripped.lower()
    for prefix, flag in _PREFIX_FLAGS:
        if low.startswith(prefix):
            stripped = stripped[len(prefix) :].strip()
            flags[flag] = True
            if flag == "steer_from_chat":
                steer_match = re.match(r"^:([a-z]+)\s*", stripped, flags=re.I)
                if steer_match:
                    surface_id = _normalize_surface_id(steer_match.group(1))
                    stripped = stripped[steer_match.end() :].strip()
            break
    return stripped, flags, surface_id


def queue_for_run(run_id: str) -> InterjectionQueue:
    key = str(run_id)
    if key not in _RUN_QUEUES:
        _RUN_QUEUES[key] = InterjectionQueue()
    return _RUN_QUEUES[key]
