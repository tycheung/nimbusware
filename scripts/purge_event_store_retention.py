#!/usr/bin/env python3
"""Event store retention purge reporting and optional execute."""

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
        help="DELETE eligible rows when NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE=1",
    )
    args = parser.parse_args()

    from nimbusware_store.retention_policy import (
        legal_hold_enabled,
        purge_eligible_before,
        purge_execute_enabled,
    )

    if legal_hold_enabled():
        print("Legal hold active (NIMBUSWARE_EVENT_STORE_LEGAL_HOLD); purge skipped")
        return 0

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
            print("Dry-run only; pass --execute to purge (requires NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE=1)")
            return 0
        if not purge_execute_enabled():
            print("Execute blocked: set NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE=1")
            return 1
        from nimbusware_store.purge import purge_events_before

        deleted = purge_events_before(conn, cutoff)
    print(f"Purged {deleted} row(s) before {cutoff.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
