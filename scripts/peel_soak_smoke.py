#!/usr/bin/env python3
"""Dual-run soak smoke harness (`sak415-j` / domain asserts sak403-f–sak407-f / sak421-b).

In-process only: sets dual-run flags inside this process for bind_plan and domain asserts.
Default flags=``1``. ``--broker-only`` sets flags to ``2`` and runs refuse-local asserts.
Does **not** flip default-on calendar or delete packages.
Soak-smoke ≠ multi-day soak — see ``docs/peel-runbook.md`` and ``docs/peel-soak-day0.md``.
"""

from __future__ import annotations

import argparse
import os
import sys

from peel_common import NIMBUSWARE_ROOT
from peel_soak_lib import (
    assert_bind_plans,
    broker_only_smoke_sections,
    domain_smoke_sections,
    run_domain_sections,
    run_dual_run_contract_pytest,
    run_prereq_checks,
    soak_env,
    try_broker_live_check,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-prereq",
        action="store_true",
        help="Skip peel_soak_prereq.py (for local iteration only)",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip dual-run contract pytest subprocess",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail when broker HTTP/MCP env is unset or live ping fails (sak415-l)",
    )
    parser.add_argument(
        "--broker-only",
        action="store_true",
        help="Set dual-run flags to 2 and run refuse-local asserts (sak421-b)",
    )
    args = parser.parse_args(argv)

    base_env = os.environ.copy()
    env = soak_env(base_env, broker_only=args.broker_only)
    mode = "2" if args.broker_only else "1"

    print("peel soak smoke (sak415-j)")
    print(f"repo: {NIMBUSWARE_ROOT}")
    print(
        f"note: flags={mode} in this harness only; soak-smoke != N-day soak; no deletes"
        + (" [--broker-only]" if args.broker_only else "")
    )

    all_ok = True

    print("\n--- prerequisites (sak415-i) ---")
    if args.skip_prereq:
        print("  [SKIP] peel_soak_prereq.py (--skip-prereq)")
    else:
        all_ok &= run_prereq_checks(base_env)

    print(f"\n--- bind_plan (all domains, flags={mode}) ---")
    for flag in env:
        if flag.startswith("NIMBUSWARE_BROKER_") and flag not in (
            "NIMBUSWARE_BROKER_HTTP",
            "NIMBUSWARE_BROKER_TOKEN",
            "NIMBUSWARE_BROKER_MCP",
        ):
            os.environ[flag] = env[flag]
    all_ok &= assert_bind_plans(env)

    sections = domain_smoke_sections()
    if args.broker_only:
        sections = (*sections, *broker_only_smoke_sections())
    all_ok &= run_domain_sections(env, sections)

    print("\n--- dual-run contract tests (pytest subprocess) ---")
    if args.skip_pytest:
        print("  [SKIP] contract pytest (--skip-pytest)")
    else:
        # Contract tests expect dual-run (=1) semantics; use flags=1 env for subprocess.
        contract_env = soak_env(base_env, broker_only=False)
        all_ok &= run_dual_run_contract_pytest(contract_env)

    print("\n--- optional broker live check (sak415-l) ---")
    live = try_broker_live_check(base_env, require_live=args.require_live)
    if live is not None:
        all_ok &= live

    print()
    print("overall:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
