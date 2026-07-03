from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from env.env_flags import nimbusware_database_url, nimbusware_repo_root_path
from orchestrator.registry import RoleRegistry
from orchestrator.role_telemetry import aggregate_recent_run_telemetry


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Aggregate Nimbusware per-role token/latency hints from recent runs.",
    )
    p.add_argument("--repo-root", type=Path, default=None, help="Repo root for roles.yaml")
    p.add_argument("--limit", type=int, default=50, help="Recent runs to scan (default 50)")
    p.add_argument("--offset", type=int, default=0, help="Offset into recent run list")
    p.add_argument(
        "--aggregate-in",
        type=Path,
        help="Skip DB read; load existing aggregate JSON (passthrough / re-export)",
    )
    p.add_argument("--out", type=Path, help="Write JSON summary (default stdout)")
    p.add_argument(
        "--persist",
        action="store_true",
        help="Upsert summary into Postgres config store (requires NIMBUSWARE_DATABASE_URL)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo = args.repo_root or nimbusware_repo_root_path()
    registry = RoleRegistry.from_yaml(repo / "configs" / "roles.yaml")

    if args.aggregate_in is not None:
        doc = json.loads(args.aggregate_in.read_text(encoding="utf-8"))
    else:
        conninfo = nimbusware_database_url() or ""
        if not conninfo:
            print("NIMBUSWARE_DATABASE_URL is required without --aggregate-in", file=sys.stderr)
            return 1
        from store.postgres import PostgresEventStore

        store = PostgresEventStore(conninfo)
        doc = aggregate_recent_run_telemetry(
            store,
            registry=registry,
            limit=max(1, min(200, args.limit)),
            offset=max(0, args.offset),
        )

    payload = json.dumps(doc, indent=2, sort_keys=True, default=str)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    if args.persist:
        conninfo = nimbusware_database_url() or ""
        if not conninfo:
            print("NIMBUSWARE_DATABASE_URL is required for --persist", file=sys.stderr)
            return 1
        from config.keys import KEY_ROLE_TELEMETRY, NS_POLICY
        from config.store import PostgresConfigStore

        PostgresConfigStore(conninfo).upsert(NS_POLICY, KEY_ROLE_TELEMETRY, doc)
        print(
            json.dumps({"persisted": True, "namespace": NS_POLICY, "key": KEY_ROLE_TELEMETRY}),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
