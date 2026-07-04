#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from standards.registry import load_facade_manifest


def _workflow_yaml(facade_id: str, *, api_url: str) -> str:
    manifest = load_facade_manifest(facade_id)
    if manifest is None:
        msg = f"unknown standards facade: {facade_id}"
        raise ValueError(msg)
    display = str(manifest.get("display_name") or facade_id)
    template = {
        "name": f"Nimbusware standards ({display})",
        "on": {"push": {"branches": ["main"]}, "pull_request": {"branches": ["main"]}},
        "jobs": {
            "standards": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v6"},
                    {
                        "name": "Run Nimbusware standards profile",
                        "env": {"NIMBUSWARE_API_URL": api_url},
                        "run": (
                            "curl -sfS -X POST "
                            f"\"${{NIMBUSWARE_API_URL}}/v1/standards/export-run\" "
                            f"-H 'Content-Type: application/json' "
                            f"-d '{{\"facade_id\":\"{facade_id}\"}}'"
                        ),
                    },
                ],
            },
        },
    }
    return yaml.safe_dump(template, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a GitHub Actions workflow template for a standards facade.",
    )
    parser.add_argument("--facade", required=True, help="Facade id from configs/standards/facades/")
    parser.add_argument(
        "--api-url",
        default="https://nimbusware.example.com",
        help="Nimbusware API base URL embedded in the workflow",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write workflow YAML to this path (default: stdout)",
    )
    args = parser.parse_args()
    try:
        content = _workflow_yaml(args.facade.strip(), api_url=args.api_url.strip())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
