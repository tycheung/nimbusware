from __future__ import annotations

from typing import Any


def build_memory_chunk_store(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError(
        "memory.factory removed (sak413); use sak memory_index / memory_search"
    )
