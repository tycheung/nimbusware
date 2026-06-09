from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


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
    ) -> InterjectionItem:
        item = InterjectionItem(
            item_id=str(uuid4()),
            message=message.strip(),
            priority=priority,
            force_break=force_break,
            build_from_chat=build_from_chat or message.strip().startswith("[build]"),
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
                }
                for i in self.items
            ],
        }


_RUN_QUEUES: dict[str, InterjectionQueue] = {}


def queue_for_run(run_id: str) -> InterjectionQueue:
    key = str(run_id)
    if key not in _RUN_QUEUES:
        _RUN_QUEUES[key] = InterjectionQueue()
    return _RUN_QUEUES[key]
