from __future__ import annotations

import argparse
import json
import sys

import httpx

from nimbusware_compute.minimal_worker import probe_minimal_worker_capabilities
from nimbusware_compute.worker_cli import run_worker_loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Minimal Nimbusware mesh worker — register, heartbeat, and execute "
            "work units without Maker UI or Postgres."
        ),
    )
    parser.add_argument("--host-url", required=True, help="Host API base URL")
    parser.add_argument("--token", default="", help="Session compute token")
    parser.add_argument("--session-id", default="", help="Collaborative session UUID")
    parser.add_argument("--host-label", default="", help="Worker host label")
    parser.add_argument(
        "--worker-base-url",
        default="http://127.0.0.1:0",
        help="Callback reachability URL advertised to host",
    )
    parser.add_argument("--interval", type=float, default=30.0, help="Heartbeat interval seconds")
    parser.add_argument("--once", action="store_true", help="Register and send one heartbeat")
    parser.add_argument("--no-pull", action="store_true", help="Heartbeat-only mode")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Print capability probe JSON and exit (no host connection)",
    )
    args = parser.parse_args(argv)

    if args.probe:
        print(json.dumps(probe_minimal_worker_capabilities(), indent=2))
        return 0

    import socket

    label = args.host_label.strip() or socket.gethostname()
    max_beats = 1 if args.once else None
    try:
        return run_worker_loop(
            host_url=args.host_url,
            session_token=args.token,
            host_label=label,
            worker_base_url=args.worker_base_url,
            session_id=args.session_id.strip(),
            interval_seconds=args.interval,
            max_heartbeats=max_beats,
            pull_work_units=not args.no_pull,
            capabilities=probe_minimal_worker_capabilities(),
        )
    except httpx.HTTPError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
