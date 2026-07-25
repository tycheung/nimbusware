#!/usr/bin/env python3
"""Peel delete dry-run (`sak411-b` / sak412-a / sak413-a / sak411-d).

Lists inventory paths that would be deleted or thinned. Never deletes files.
"""

from __future__ import annotations

import argparse
import sys

from peel_common import DOMAIN_CANDIDATES, NIMBUSWARE_ROOT, candidate_rows

# Aggregated domains for --domain all (tools aliases sandbox; listed separately via keys).
ALL_DOMAINS: tuple[str, ...] = (
    "llm",
    "sandbox",
    "memory",
    "research",
    "egress",
    "compute",
    "capacity",
)


def _domain_choices() -> list[str]:
    """Choices include every DOMAIN_CANDIDATES key so future domains dry-run without code churn."""
    return ["all", *sorted(DOMAIN_CANDIDATES.keys())]


def run_domain(domain: str, *, strict: bool) -> tuple[int, int]:
    """Print one domain report. Returns (missing_count, exit_hint)."""
    rows = candidate_rows(NIMBUSWARE_ROOT, domain)
    missing = [candidate for candidate, exists in rows if not exists]

    print(f"peel delete dry-run — domain={domain} (NO DELETE)")
    print(f"repo: {NIMBUSWARE_ROOT}")
    print(f"candidates: {len(rows)}")
    print("paths:")

    for candidate, exists in rows:
        exist_label = "yes" if exists else "no"
        print(f"  [{candidate.action}] {candidate.rel_path}  exist={exist_label}")

    if missing:
        print(f"missing: {len(missing)} path(s) not on disk")
        for candidate in missing:
            print(f"  - {candidate.rel_path}")
    else:
        print("missing: none")

    if strict and missing:
        return len(missing), 1
    return len(missing), 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain",
        required=True,
        choices=_domain_choices(),
        help=(
            "Peel domain inventory to report (sandbox == tools list; "
            "all = ALL_DOMAINS aggregate; any DOMAIN_CANDIDATES key is valid)"
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when an inventory path is missing from disk (unexpected pre-delete)",
    )
    args = parser.parse_args(argv)

    domains = list(ALL_DOMAINS) if args.domain == "all" else [args.domain]
    any_fail = False
    total_missing = 0

    for i, domain in enumerate(domains):
        if i > 0:
            print()
        missing, code = run_domain(domain, strict=args.strict)
        total_missing += missing
        if code != 0:
            any_fail = True

    if args.domain == "all":
        print()
        print(
            f"peel delete dry-run — domain=all summary: "
            f"domains={len(domains)} missing_total={total_missing} (NO DELETE)"
        )

    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
