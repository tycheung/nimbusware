#!/usr/bin/env python3
"""Peel delete inventory path guard (`sak414-d`, `sak416-f/g`).

Pre-delete (default): inventory paths are expected to **exist** — warn only.
Post-delete (``--post-delete``):
  - ``delete`` action paths must be **gone**
  - ``thin`` action paths must **remain** (broker-only stubs)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from peel_common import DOMAIN_CANDIDATES, NIMBUSWARE_ROOT, PeelCandidate, path_exists


def inventory_candidates() -> tuple[PeelCandidate, ...]:
    """Unique inventory rows from ``peel_common.DOMAIN_CANDIDATES``."""
    seen: set[str] = set()
    out: list[PeelCandidate] = []
    for domain in sorted(DOMAIN_CANDIDATES):
        for candidate in DOMAIN_CANDIDATES[domain]:
            if candidate.rel_path in seen:
                continue
            seen.add(candidate.rel_path)
            out.append(candidate)
    return tuple(out)


def scan_inventory(root: Path) -> tuple[list[PeelCandidate], list[PeelCandidate]]:
    existing: list[PeelCandidate] = []
    missing: list[PeelCandidate] = []
    for candidate in inventory_candidates():
        if path_exists(root, candidate.rel_path):
            existing.append(candidate)
        else:
            missing.append(candidate)
    return existing, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=NIMBUSWARE_ROOT,
        help="Repo root containing packages/ (for tests)",
    )
    parser.add_argument(
        "--post-delete",
        action="store_true",
        help="Fail when delete paths remain or thin stubs are missing",
    )
    args = parser.parse_args(argv)

    existing, missing = scan_inventory(args.root)
    total = len(existing) + len(missing)

    if args.post_delete:
        still_present = [c for c in existing if c.action == "delete"]
        thin_missing = [c for c in missing if c.action == "thin"]
        if still_present or thin_missing:
            print(
                f"peel delete guard post-delete: FAIL — "
                f"{len(still_present)} delete path(s) still exist, "
                f"{len(thin_missing)} thin stub(s) missing "
                f"(of {total} inventory rows)",
                file=sys.stderr,
            )
            for candidate in still_present:
                print(f"  still present: [{candidate.action}] {candidate.rel_path}", file=sys.stderr)
            for candidate in thin_missing:
                print(f"  thin missing: [{candidate.action}] {candidate.rel_path}", file=sys.stderr)
            return 1
        deleted = len([c for c in missing if c.action == "delete"])
        thinned = len([c for c in existing if c.action == "thin"])
        print(
            f"peel delete guard post-delete: ok "
            f"({deleted} delete path(s) absent, {thinned} thin stub(s) present)"
        )
        return 0

    if existing:
        print(
            f"peel delete guard pre-delete: warn — {len(existing)}/{total} inventory path(s) "
            "still exist (expected before sak411+)"
        )
        for candidate in existing[:8]:
            print(f"  present: [{candidate.action}] {candidate.rel_path}")
        if len(existing) > 8:
            print(f"  ... and {len(existing) - 8} more")
    else:
        print("peel delete guard pre-delete: no inventory paths on disk (unexpected pre-delete?)")

    if missing:
        print(f"  missing: {len(missing)} inventory path(s) not found")

    print("peel delete guard pre-delete: ok (no-op/warn mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
