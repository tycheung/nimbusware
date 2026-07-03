from __future__ import annotations

from collections.abc import Callable
from typing import Any


def emit_stub_or_live_from_gate(
    gated: tuple[Any, Any, Any, Any],
    *,
    emit_stub: Callable[[Any], None],
    emit_live: Callable[[Any], None],
) -> None:
    _tri, _rows, _wf, block = gated
    if block.stub_only:
        emit_stub(block)
    else:
        emit_live(block)
