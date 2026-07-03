from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

from env.env_flags import nimbusware_database_url

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rebuild repo-scoped Nimbusware memory index.")
    p.add_argument("--repo-root", type=Path, default=ROOT)
    p.add_argument(
        "--audit-run-id",
        type=str,
        required=True,
        help="Run UUID to attach memory.indexed audit event",
    )
    args = p.parse_args(argv)
    conninfo = nimbusware_database_url() or ""
    if not conninfo:
        print("NIMBUSWARE_DATABASE_URL is required", file=sys.stderr)
        return 1
    from memory.index.indexer import rebuild_memory_index
    from memory.store.postgres import PostgresMemoryChunkStore
    from store.postgres import PostgresEventStore

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
