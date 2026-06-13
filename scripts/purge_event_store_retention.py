#!/usr/bin/env python3
"""Dry-run event_store retention purge reporting (append-only schema blocks DELETE)."""

from __future__ import annotations

import argparse
import os
import sys

import psycopg


def _database_url() -> str:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("NIMBUSWARE_DATABASE_URL is required")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Event store retention purge helper")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Attempt DELETE (blocked by append-only triggers unless operator overrides schema)",
    )
    args = parser.parse_args()

    from nimbusware_store.retention_policy import purge_eligible_before

    cutoff = purge_eligible_before()
    if cutoff is None:
        print("Retention disabled (NIMBUSWARE_EVENT_STORE_RETENTION_DAYS unset or 0)")
        return 0

    with psycopg.connect(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM event_store WHERE occurred_at < %s",
                (cutoff,),
            )
            count = int(cur.fetchone()[0])
    print(f"Eligible rows before {cutoff.isoformat()}: {count}")
    if not args.execute:
        print("Dry-run only; pass --execute to attempt purge (requires schema override)")
        return 0
    print("Execute purge is not enabled while append-only triggers are active.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
