"""CLI entry for Hermes memory index rebuild."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rebuild repo-scoped Hermes memory index.")
    p.add_argument("--repo-root", type=Path, default=ROOT)
    p.add_argument(
        "--audit-run-id",
        type=str,
        required=True,
        help="Run UUID to attach memory.indexed audit event",
    )
    args = p.parse_args(argv)
    conninfo = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not conninfo:
        print("NIMBUSWARE_DATABASE_URL is required", file=sys.stderr)
        return 1
    from hermes_memory.indexer import rebuild_memory_index
    from hermes_memory.store import PostgresMemoryChunkStore
    from hermes_store.postgres import PostgresEventStore

    store = PostgresMemoryChunkStore(conninfo)
    audit_store = PostgresEventStore(conninfo)
    result = rebuild_memory_index(
        store,
        repo_root=args.repo_root.resolve(),
        conninfo=conninfo,
        audit_store=audit_store,
        audit_run_id=UUID(str(args.audit_run_id)),
    )
    print(
        f"memory index generation={result.generation_id} "
        f"chunks={result.chunks_added} skipped={result.chunks_skipped}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
