"""Enterprise fleet memory sync CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    from nimbusware_memory.fleet_sync import (
        pull_fleet_memory_from_canonical,
        push_fleet_memory_to_canonical,
    )
    from nimbusware_memory.org_scope import require_fleet_memory_feature
    from nimbusware_memory.store import InMemoryMemoryChunkStore, PostgresMemoryChunkStore

    try:
        require_fleet_memory_feature()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    p = argparse.ArgumentParser(description="Enterprise fleet memory canonical sync.")
    sub = p.add_subparsers(dest="command", required=True)

    push_p = sub.add_parser("push", help="Upload latest fleet generation to canonical store")
    push_p.add_argument("--org-slug", default="default")
    push_p.add_argument("--canonical-root", type=Path, default=None)

    pull_p = sub.add_parser("pull", help="Hydrate local store from canonical fleet bundle")
    pull_p.add_argument("--org-slug", default="default")
    pull_p.add_argument("--generation-id", default=None)
    pull_p.add_argument("--canonical-root", type=Path, default=None)

    args = p.parse_args(argv)
    conninfo = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    memory_store: PostgresMemoryChunkStore | InMemoryMemoryChunkStore
    if conninfo:
        memory_store = PostgresMemoryChunkStore(conninfo)
    else:
        memory_store = InMemoryMemoryChunkStore()

    try:
        if args.command == "push":
            out = push_fleet_memory_to_canonical(
                memory_store,
                canonical_root=args.canonical_root,
                org_slug=args.org_slug,
            )
            print(
                f"pushed org_scope={out['org_scope_hash']} "
                f"generation={out['generation_id']} chunks={out['chunk_count']}",
            )
            return 0
        out = pull_fleet_memory_from_canonical(
            memory_store,
            canonical_root=args.canonical_root,
            org_slug=args.org_slug,
            generation_id=args.generation_id,
        )
        print(
            f"pulled org_scope={out['org_scope_hash']} "
            f"generation={out['generation_id']} chunks={out['chunk_count']}",
        )
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
