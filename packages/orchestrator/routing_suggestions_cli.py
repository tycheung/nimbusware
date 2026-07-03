from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from env.env_flags import nimbusware_database_url, nimbusware_repo_root_path
from orchestrator.merge import load_yaml
from orchestrator.registry import RoleRegistry
from orchestrator.role_telemetry import aggregate_recent_run_telemetry
from orchestrator.routing.suggestions import (
    enrich_aggregate_with_model_selection,
    suggest_model_routing_changes,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Suggest model-routing.yaml tweaks from role telemetry aggregates. "
            "Read-only — apply via nimbusware-config after operator review."
        ),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--routing",
        type=Path,
        help="model-routing.yaml path (default: <repo>/configs/model-routing.yaml)",
    )
    p.add_argument(
        "--aggregate",
        type=Path,
        help="Existing telemetry aggregate JSON (skip DB scan)",
    )
    p.add_argument("--limit", type=int, default=50, help="Recent runs when scanning DB")
    p.add_argument("--out", type=Path, help="Write suggestions JSON (default stdout)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo = args.repo_root or nimbusware_repo_root_path()
    routing_path = (args.routing or repo / "configs" / "model-routing.yaml").resolve()
    routing = load_yaml(routing_path)
    registry = RoleRegistry.from_yaml(repo / "configs" / "roles.yaml")

    rows: list[dict] = []
    if args.aggregate is not None:
        aggregate = json.loads(args.aggregate.read_text(encoding="utf-8"))
    else:
        conninfo = nimbusware_database_url() or ""
        if not conninfo:
            print("NIMBUSWARE_DATABASE_URL or --aggregate is required", file=sys.stderr)
            return 1
        from store.postgres import PostgresEventStore

        store = PostgresEventStore(conninfo)
        run_ids = store.list_recent_run_ids(
            limit=max(1, min(200, args.limit)),
            offset=0,
            order="newest_first",
        )
        ids = [str(rid) for rid in run_ids]
        if hasattr(store, "list_run_events_many"):
            row_map = store.list_run_events_many(ids)
            for rid in ids:
                rows.extend(row_map.get(rid, []))
        else:
            for rid in ids:
                rows.extend(store.list_run_events(rid))
        aggregate = aggregate_recent_run_telemetry(
            store,
            registry=registry,
            limit=max(1, min(200, args.limit)),
        )

    if rows:
        aggregate = enrich_aggregate_with_model_selection(aggregate, rows)

    suggestions = suggest_model_routing_changes(aggregate, routing)
    output = {
        "schema_version": 1,
        "routing_path": str(routing_path),
        "aggregate_schema_version": aggregate.get("schema_version"),
        "run_count": aggregate.get("run_count"),
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "read_only": True,
        "apply_hint": "Review suggestions, edit configs/model-routing.yaml, then: poetry run nimbusware-config import",
    }
    payload = json.dumps(output, indent=2, sort_keys=True, default=str)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
