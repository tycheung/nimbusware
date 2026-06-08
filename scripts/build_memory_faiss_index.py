#!/usr/bin/env python3
"""Build optional FAISS index for repo-scoped Nimbusware memory chunks.

Requires: ``poetry install --with faiss`` when building the vector index.

Reads chunk rows from Postgres (``NIMBUSWARE_DATABASE_URL``) or rebuilds from the
in-memory event store path used in tests. Writes under ``configs/memory/index/`` by default.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build Nimbusware memory FAISS index.")
    p.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root (default: script parent)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: <repo-root>/configs/memory/index)",
    )
    p.add_argument(
        "--rebuild-metadata",
        action="store_true",
        help="Rebuild Postgres/in-memory chunk metadata before FAISS build",
    )
    p.add_argument(
        "--audit-run-id",
        type=str,
        default=None,
        help="Optional run UUID for memory.indexed audit event (requires Postgres store)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    repo = args.repo_root.resolve()
    from nimbusware_memory.manifest import default_memory_index_dir
    from nimbusware_memory.faiss_index import build_memory_faiss_index, memory_faiss_index_ready
    from nimbusware_memory.store import InMemoryMemoryChunkStore, PostgresMemoryChunkStore

    out_dir = (args.out_dir or default_memory_index_dir(repo)).resolve()
    conninfo = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if args.rebuild_metadata:
        from uuid import UUID

        from nimbusware_memory.indexer import rebuild_memory_index

        if conninfo:
            mem_store: InMemoryMemoryChunkStore | PostgresMemoryChunkStore = PostgresMemoryChunkStore(
                conninfo,
            )
            audit_store = None
            audit_run_id = None
            if args.audit_run_id:
                from nimbusware_store.postgres import PostgresEventStore

                audit_store = PostgresEventStore(conninfo)
                audit_run_id = UUID(str(args.audit_run_id))
            rebuild_memory_index(
                mem_store,
                repo_root=repo,
                conninfo=conninfo,
                audit_store=audit_store,
                audit_run_id=audit_run_id,
            )
        else:
            print(
                "NIMBUSWARE_DATABASE_URL required for --rebuild-metadata",
                file=sys.stderr,
            )
            return 1
    else:
        if not conninfo:
            print(
                "NIMBUSWARE_DATABASE_URL required unless --rebuild-metadata with test fixtures",
                file=sys.stderr,
            )
            return 1
        mem_store = PostgresMemoryChunkStore(conninfo)
        from nimbusware_memory.repo_scope import repo_scope_hash

        scope = repo_scope_hash(repo)
        chunks = mem_store.list_chunks_for_scope(scope)
        code = build_memory_faiss_index(chunks=chunks, index_dir=out_dir)
        if code != 0:
            print("FAISS build failed (install faiss group or no chunks)", file=sys.stderr)
            return code
    if memory_faiss_index_ready(out_dir):
        print(f"Memory FAISS index ready under {out_dir}")
        return 0
    print("Memory FAISS index not written (optional faiss group missing?)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
