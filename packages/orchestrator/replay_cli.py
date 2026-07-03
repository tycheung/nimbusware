from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from env.env_flags import nimbusware_database_url
from orchestrator.replay_harness import (
    build_replay_snapshot,
    diff_replay_snapshots,
    load_fixture_rows,
    load_run_rows_from_store,
    stable_replay_hash,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Replay Nimbusware event-store rows into timeline JSON + stable hash.",
    )
    p.add_argument(
        "run_id",
        nargs="?",
        help="Run UUID to replay from Postgres (requires NIMBUSWARE_DATABASE_URL)",
    )
    p.add_argument(
        "--fixture",
        type=Path,
        help="Replay anonymized fixture JSON instead of Postgres",
    )
    p.add_argument(
        "--out",
        type=Path,
        help="Write replay JSON to path (default: stdout)",
    )
    p.add_argument(
        "--hash",
        action="store_true",
        help="Print stable SHA-256 hash only",
    )
    p.add_argument(
        "--diff",
        type=Path,
        help="Compare replay snapshot against golden JSON file",
    )
    p.add_argument(
        "--diff-run",
        type=str,
        help="Compare replay against another run_id in Postgres",
    )
    return p


def _load_rows(args: argparse.Namespace) -> tuple[str | None, list[dict]]:
    if args.fixture is not None:
        return load_fixture_rows(args.fixture.resolve())
    run_id = (args.run_id or "").strip()
    if not run_id:
        print("run_id or --fixture is required", file=sys.stderr)
        raise SystemExit(2)
    try:
        UUID(run_id)
    except ValueError:
        print(f"invalid run_id UUID: {run_id}", file=sys.stderr)
        raise SystemExit(2) from None
    conninfo = nimbusware_database_url() or ""
    if not conninfo:
        print("NIMBUSWARE_DATABASE_URL is required without --fixture", file=sys.stderr)
        raise SystemExit(1)
    from store.postgres import PostgresEventStore

    store = PostgresEventStore(conninfo)
    rows = load_run_rows_from_store(store, run_id)
    if not rows:
        print(f"run not found or empty: {run_id}", file=sys.stderr)
        raise SystemExit(1)
    return run_id, rows


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run_id, rows = _load_rows(args)
    snapshot = build_replay_snapshot(rows, run_id=run_id)
    if args.hash:
        print(stable_replay_hash(snapshot))
        return 0
    if args.diff is not None:
        golden_raw = json.loads(args.diff.read_text(encoding="utf-8"))
        if isinstance(golden_raw, dict) and "summary" in golden_raw:
            expected = golden_raw
        else:
            expected = build_replay_snapshot(
                golden_raw if isinstance(golden_raw, list) else golden_raw.get("rows", []),
                run_id=run_id,
            )
        lines = diff_replay_snapshots(expected, snapshot, left_label="golden", right_label="live")
        if lines:
            for line in lines:
                print(line)
            return 1
        print("replay snapshot matches golden")
        return 0
    if args.diff_run:
        conninfo = nimbusware_database_url() or ""
        if not conninfo:
            print("NIMBUSWARE_DATABASE_URL is required for --diff-run", file=sys.stderr)
            return 1
        from store.postgres import PostgresEventStore

        other_rows = load_run_rows_from_store(PostgresEventStore(conninfo), args.diff_run)
        other = build_replay_snapshot(other_rows, run_id=args.diff_run)
        lines = diff_replay_snapshots(
            snapshot,
            other,
            left_label=str(run_id),
            right_label=args.diff_run,
        )
        if lines:
            for line in lines:
                print(line)
            return 1
        print("replay snapshots match")
        return 0
    payload = json.dumps(snapshot, indent=2, sort_keys=True, default=str)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
