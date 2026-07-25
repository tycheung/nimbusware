#!/usr/bin/env python3
"""Peel rollout checklist (`sak415-b`). Informational status for flags, audit, and CI."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
AGENTIC_DOCS = ROOT.parent / "docs"
PEEL_RUNBOOK = AGENTIC_DOCS / "peel-runbook.md"

_DEFAULT_ON_GATE_MARKER = "Default-on gate"
_GATE_SUSPENDED_MARKER = "TEMPORARILY SUSPENDED"

_FLAG_NAMES = (
    "NIMBUSWARE_BROKER_LLM",
    "NIMBUSWARE_BROKER_SANDBOX",
    "NIMBUSWARE_BROKER_TOOLS",
    "NIMBUSWARE_BROKER_MEMORY",
    "NIMBUSWARE_BROKER_RESEARCH",
    "NIMBUSWARE_BROKER_EGRESS",
    "NIMBUSWARE_BROKER_COMPUTE",
    "NIMBUSWARE_BROKER_CAPACITY",
)

_BRIDGE_MODULES = (
    "research.research_bridge",
    "research.fetch",
    "agent_tools.memory_bridge",
    "agent_tools.sandbox_bridge",
    "broker_client.compute_bridge",
    "broker_client.capacity_bridge",
    "executor.egress_bridge",
    "orchestrator.llm.broker_bridge",
)

_STAGE_BIND_MODULES = (
    "broker_client.stage_bind.llm",
    "broker_client.stage_bind.sandbox",
    "broker_client.stage_bind.memory",
    "broker_client.stage_bind.research",
    "broker_client.stage_bind.compute",
    "broker_client.stage_bind.capacity",
    "broker_client.stage_bind.tools",
)

_BRIDGE_FILES = (
    ROOT / "packages" / "research" / "fetch.py",
    ROOT / "packages" / "research" / "research_bridge.py",
    ROOT / "packages" / "agent_tools" / "memory_bridge.py",
    ROOT / "packages" / "agent_tools" / "sandbox_bridge.py",
    ROOT / "packages" / "broker_client" / "compute_bridge.py",
    ROOT / "packages" / "executor" / "egress_bridge.py",
)


def _module_importable(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _broker_client_importable() -> bool:
    return _module_importable("broker_client")


def _audit_counts() -> dict[str, int]:
    sys.path.insert(0, str(SCRIPTS))
    try:
        from audit_reverse_imports import collect_all_packages
    finally:
        if str(SCRIPTS) in sys.path:
            sys.path.remove(str(SCRIPTS))

    packages = collect_all_packages(root=ROOT)
    return {pkg: len(findings) for pkg, findings in packages.items()}


def _forbidden_counts() -> dict[str, int]:
    sys.path.insert(0, str(SCRIPTS))
    try:
        from ci_peel_import_graph import forbidden_hits_by_package
    finally:
        if str(SCRIPTS) in sys.path:
            sys.path.remove(str(SCRIPTS))

    grouped = forbidden_hits_by_package(root=ROOT)
    return {pkg: len(hits) for pkg, hits in grouped.items()}


def _bridge_status() -> list[tuple[str, bool, bool]]:
    rows: list[tuple[str, bool, bool]] = []
    for path in _BRIDGE_FILES:
        label = str(path.relative_to(ROOT)).replace("\\", "/")
        rows.append((label, path.is_file(), path.is_file()))
    for mod in _BRIDGE_MODULES:
        ok = _module_importable(mod)
        rows.append((mod, ok, ok))
    for mod in _STAGE_BIND_MODULES:
        ok = _module_importable(mod)
        rows.append((mod, ok, ok))
    return rows


def _bridges_ok() -> bool:
    for _label, file_ok, import_ok in _bridge_status():
        if not (file_ok and import_ok):
            return False
    return True


def _runbook_text() -> str:
    if not PEEL_RUNBOOK.is_file():
        return ""
    return PEEL_RUNBOOK.read_text(encoding="utf-8")


def _gate_suspended() -> bool:
    return _GATE_SUSPENDED_MARKER in _runbook_text()


def _default_on_gate_doc_ok() -> bool:
    """True when peel-runbook contains the default-on gate section (`sak415-e`).

    While the gate is TEMPORARILY SUSPENDED, the section (with suspension banner)
    still satisfies this doc check; multi-day calendar soak is not enforced.
    """
    text = _runbook_text()
    if not text:
        return False
    return _DEFAULT_ON_GATE_MARKER in text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero when broker_client/bridges are not ready, "
            "forbidden edges are present, or default-on gate doc is missing. "
            "Does not fail solely because multi-day soak is incomplete while "
            "the gate is TEMPORARILY SUSPENDED."
        ),
    )
    parser.add_argument(
        "--require-soak-gate",
        action="store_true",
        help=(
            "Fail --strict-style when the default-on gate is TEMPORARILY "
            "SUSPENDED (used after gate re-implement). Alone does nothing; "
            "combine with --strict."
        ),
    )
    args = parser.parse_args(argv)

    print("peel checklist (sak415-b/c/e)")
    print(f"repo: {ROOT}")

    print("dual-run flags:")
    for name in _FLAG_NAMES:
        print(f"  {name}={os.environ.get(name, '(unset)')}")

    importable = _broker_client_importable()
    print(f"broker_client importable: {'yes' if importable else 'no'}")

    print("peel bridges + stage_bind:")
    for label, file_ok, import_ok in _bridge_status():
        status = "ok" if (file_ok and import_ok) else "MISSING"
        print(f"  [{status}] {label}")
    bridges_ready = _bridges_ok()
    print(f"bridges ready: {'yes' if bridges_ready else 'no'}")

    audit = _audit_counts()
    print("reverse-import audit:")
    for pkg, count in sorted(audit.items()):
        print(f"  {pkg}->orchestrator: {count} site(s)")

    forbidden = _forbidden_counts()
    print("CI forbidden edges:")
    if forbidden:
        for pkg, count in sorted(forbidden.items()):
            print(f"  {pkg}: {count} hit(s)")
    else:
        print("  (none)")

    ci_script = SCRIPTS / "ci_peel_import_graph.py"
    print(f"ci_peel_import_graph.py: {'present' if ci_script.is_file() else 'missing'}")

    gate_doc_ok = _default_on_gate_doc_ok()
    suspended = _gate_suspended()
    if suspended:
        print("default-on gate doc (`sak415-e`): ok (TEMPORARILY SUSPENDED — calendar soak not enforced)")
    elif gate_doc_ok:
        print("default-on gate doc (`sak415-e`): ok (ACTIVE)")
    else:
        print("default-on gate doc (`sak415-e`): MISSING")

    if not args.strict:
        return 0

    if not importable:
        print("strict: fail — broker_client not importable", file=sys.stderr)
        return 1
    if not bridges_ready:
        print("strict: fail — bridges/stage_bind not ready", file=sys.stderr)
        return 1
    if forbidden:
        print("strict: fail — forbidden import edges present", file=sys.stderr)
        return 1
    if not gate_doc_ok:
        print("strict: fail — default-on gate doc missing", file=sys.stderr)
        return 1
    # After gate restore: --require-soak-gate (or both) rejects a suspension banner.
    if args.require_soak_gate and suspended:
        print(
            "strict: fail — --require-soak-gate set but gate is TEMPORARILY SUSPENDED",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
