from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from env.edition import ENTERPRISE_EDITION, ENV_EDITION, edition
from orchestrator.fleet.ollama_sli import (
    export_path,
    run_sustained_health_probe,
    write_sli_export,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enterprise sustained Ollama health p95 probe",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Ollama base URL (default: NIMBUSWARE_FLEET_OLLAMA_SLI_BASE_URL or localhost:11434)",
    )
    parser.add_argument("--samples", type=int, default=None, help="Override sample count")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=None,
        help="Sleep between probes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"JSON export path (default: {export_path()})",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON to stdout without writing export file",
    )
    parser.add_argument(
        "--require-enterprise",
        action="store_true",
        default=True,
        help="Exit 2 when NIMBUSWARE_EDITION is not enterprise",
    )
    args = parser.parse_args(argv)
    if args.require_enterprise and edition() != ENTERPRISE_EDITION:
        print(
            f"nimbusware-fleet-ollama-sli requires {ENV_EDITION}={ENTERPRISE_EDITION} "
            f"(current: {edition()!r})",
            file=sys.stderr,
        )
        return 2
    record = run_sustained_health_probe(
        base_url=args.base_url or None,
        samples=args.samples,
        interval_seconds=args.interval_seconds,
    )
    line = json.dumps(record, separators=(",", ":"))
    print(line)
    if not args.stdout_only:
        target = write_sli_export(record, args.output)
        print(f"wrote {target}", file=sys.stderr)
    errors = record.get("probe_errors") or []
    return 1 if errors and len(errors) >= int(record.get("samples_used") or 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
