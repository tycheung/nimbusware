#!/usr/bin/env python3
"""Automated soak prerequisite checks (`sak415-i`).

Prereq-only: does not enable dual-run flags or contact a live broker.
"""

from __future__ import annotations

import argparse
import os
import sys

from peel_common import (
    AGENTIC_DOCS,
    NIMBUSWARE_ROOT,
    PEEL_DELETE_INVENTORY,
    PEEL_SOAK_LOG,
    default_on_gate_doc_ok,
    run_peel_script,
)


def _print_check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line = f"{line} — {detail}"
    print(line)
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "packages;tests")

    print("peel soak prerequisites (sak415-i)")
    print(f"repo: {NIMBUSWARE_ROOT}")
    print("checks:")

    all_ok = True

    checklist = run_peel_script("peel_checklist.py", "--strict", env=env)
    all_ok &= _print_check(
        "peel_checklist.py --strict",
        checklist.returncode == 0,
        f"exit {checklist.returncode}",
    )
    if checklist.stdout.strip():
        for line in checklist.stdout.strip().splitlines()[:3]:
            print(f"    {line}")

    import_graph = run_peel_script("ci_peel_import_graph.py", env=env)
    all_ok &= _print_check(
        "ci_peel_import_graph.py",
        import_graph.returncode == 0,
        f"exit {import_graph.returncode}",
    )

    gate_ok = default_on_gate_doc_ok()
    all_ok &= _print_check(
        "default-on gate section in peel-runbook.md",
        gate_ok,
        str(AGENTIC_DOCS / "peel-runbook.md"),
    )

    inventory_ok = PEEL_DELETE_INVENTORY.is_file()
    all_ok &= _print_check(
        "peel-delete-inventory.md exists",
        inventory_ok,
        str(PEEL_DELETE_INVENTORY),
    )

    soak_log_ok = PEEL_SOAK_LOG.is_file()
    all_ok &= _print_check(
        "peel-soak-log.md exists",
        soak_log_ok,
        str(PEEL_SOAK_LOG),
    )

    print(f"overall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
