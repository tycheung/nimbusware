#!/usr/bin/env python3
"""Audit operator env var reads under packages/ against settings catalog."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"

ENV_GET = re.compile(
    r'os\.environ\.get\(\s*["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']',
)
ENV_SETITEM = re.compile(
    r'os\.environ\[["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']\]\s*=',
)
SETENV = re.compile(
    r'(?:monkeypatch\.)?setenv\(\s*["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']',
)

# Files allowed to read install vars before Postgres store is available.
BOOTSTRAP_REL = frozenset(
    {
        "nimbusware_env/settings_store.py",
        "nimbusware_env/dotenv.py",
        "nimbusware_env/admin_token.py",
        "nimbusware_env/edition.py",
        "nimbusware_env/run_app.py",
        "nimbusware_env/admin_token.py",
        "nimbusware_orchestrator/preflight_cli.py",
        "nimbusware_orchestrator/run_dispatch.py",
        "nimbusware_orchestrator/fleet_worker.py",
        "nimbusware_orchestrator/replay_cli.py",
        "nimbusware_orchestrator/routing_suggestions_cli.py",
        "nimbusware_orchestrator/telemetry_cli.py",
        "nimbusware_orchestrator/scraper_object_store.py",
        "nimbusware_orchestrator/ollama_manage.py",
        "nimbusware_orchestrator/llm/common.py",
        "nimbusware_memory/cli.py",
        "nimbusware_memory/sync_cli.py",
        "nimbusware_memory/embeddings.py",
        "nimbusware_extensions/bundle_memory_factory.py",
        "nimbusware_api/routes/runs/lifecycle.py",
        "nimbusware_maker/onboarding.py",
        "nimbusware_maker/session.py",
        "nimbusware_maker/cli.py",
        "nimbusware_env/admin_cli.py",
        "nimbusware_env/launcher_app.py",
        "nimbusware_env/desktop_common.py",
        "nimbusware_client/http.py",
        "nimbusware_orchestrator/runtime_bootstrap.py",
        "nimbusware_config/cli.py",
        "nimbusware_config/materializer.py",
        "nimbusware_api/app.py",
        "nimbusware_api/cli.py",
        "nimbusware_maker/store.py",
        "nimbusware_memory/factory.py",
        "nimbusware_memory/contribution.py",
        "nimbusware_memory/event_scan.py",
        "nimbusware_memory/remote_store.py",
        "nimbusware_memory/repo_scope.py",
        "nimbusware_research/enterprise_index.py",
        "nimbusware_api/routes/enterprise/fleet_memory.py",
        "nimbusware_console/config_materializer.py",
        "nimbusware_console/integrator_workflow_apply.py",
        "nimbusware_console/settings.py",
        "nimbusware_env/settings_resolve.py",
        "nimbusware_env/env_flags.py",
    },
)

# Managed keys may be written to os.environ only from the settings store sync.
ENV_WRITE_ALLOW = frozenset(
    {
        "nimbusware_env/settings_store.py",
        "nimbusware_env/dotenv.py",
        "nimbusware_env/admin_token.py",
        "nimbusware_env/run_app.py",
        "nimbusware_env/launcher_app.py",
        "nimbusware_orchestrator/preflight_cli.py",
        "scripts/install_nimbusware.py",
        "scripts/ollama_setup.py",
    },
)


def _rel(path: Path) -> str:
    return path.relative_to(PACKAGES).as_posix()


def audit(*, strict_writes: bool = True) -> list[str]:
    from nimbusware_env.settings_catalog import CATALOG, SettingScope

    errors: list[str] = []
    for py in sorted(PACKAGES.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = _rel(py)
        text = py.read_text(encoding="utf-8", errors="ignore")
        for pat in (ENV_GET, SETENV):
            for m in pat.finditer(text):
                key = m.group(1)
                if key not in CATALOG:
                    errors.append(f"{rel}: unknown env key {key!r}")
                    continue
                scope = CATALOG[key].scope
                if rel not in BOOTSTRAP_REL and scope == SettingScope.INSTALL:
                    errors.append(
                        f"{rel}: install key {key!r} must use env_flags/bootstrap helpers",
                    )
        if strict_writes:
            for m in ENV_SETITEM.finditer(text):
                key = m.group(1)
                if key not in CATALOG:
                    errors.append(f"{rel}: unknown env write {key!r}")
                elif rel not in ENV_WRITE_ALLOW and CATALOG[key].scope != SettingScope.INTERNAL:
                    errors.append(
                        f"{rel}: managed env write {key!r} not allowed (use settings store)",
                    )
    return errors


def main() -> int:
    sys.path.insert(0, str(REPO / "packages"))
    errs = audit()
    if errs:
        print("Operator env audit FAILED:\n" + "\n".join(errs), file=sys.stderr)
        return 1
    from nimbusware_env.settings_catalog import CATALOG

    print(f"Operator env audit OK ({len(CATALOG)} catalog keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
