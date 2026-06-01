"""Split hermes_memory/store.py and normalize double-spaced formatting."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STORE = REPO / "packages/hermes_memory/store.py"


def _normalize(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if not ln.strip():
            if out and out[-1] == "":
                continue
            out.append("")
        else:
            out.append(ln)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def _split_blocks(text: str) -> tuple[str, str, str, str]:
    """Return header, in_memory, postgres, chunk_helper blocks."""
    in_mem = text.index("class InMemoryMemoryChunkStore:")
    postgres = text.index("class PostgresMemoryChunkStore:")
    chunk_fn = text.index("def _chunk_from_row(")
    header = text[:in_mem]
    mem = text[in_mem:postgres]
    pg = text[postgres:chunk_fn]
    tail = text[chunk_fn:]
    return header, mem, pg, tail


def main() -> None:
    raw = STORE.read_text(encoding="utf-8")
    text = _normalize(raw)
    header, mem, pg, tail = _split_blocks(text)

    pkg = REPO / "packages/hermes_memory"
    protocol_header = '''"""Memory store protocol and shared row types."""

'''
    memory_header = '''"""In-memory memory chunk store (tests)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from hermes_memory.models import EmbeddingMode, MemoryChunkRecord
from hermes_memory.store_protocol import IndexGenerationRow, MemoryChunkStore, _resolve_tenant

'''
    postgres_header = '''"""Postgres-backed memory chunk store."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from hermes_memory.models import EmbeddingMode, MemoryChunkRecord
from hermes_memory.store_protocol import IndexGenerationRow, _resolve_tenant

'''

    (pkg / "store_protocol.py").write_text(protocol_header + header, encoding="utf-8")
    (pkg / "store_memory.py").write_text(memory_header + mem, encoding="utf-8")
    (pkg / "store_postgres.py").write_text(postgres_header + pg + "\n" + tail, encoding="utf-8")

    facade = '''"""Memory chunk persistence (Postgres + in-memory for tests)."""

from hermes_memory.store_memory import InMemoryMemoryChunkStore
from hermes_memory.store_postgres import PostgresMemoryChunkStore
from hermes_memory.store_protocol import IndexGenerationRow, MemoryChunkStore

__all__ = [
    "IndexGenerationRow",
    "InMemoryMemoryChunkStore",
    "MemoryChunkStore",
    "PostgresMemoryChunkStore",
]
'''
    STORE.write_text(facade, encoding="utf-8")
    for rel in ("store_protocol.py", "store_memory.py", "store_postgres.py", "store.py"):
        n = len((pkg / rel).read_text(encoding="utf-8").splitlines())
        print(f"wrote hermes_memory/{rel} ({n} lines)")


if __name__ == "__main__":
    main()
