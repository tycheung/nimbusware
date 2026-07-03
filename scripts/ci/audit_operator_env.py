#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
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
ENV_HELPER = re.compile(
    r"(?:env_str|env_bool|env_truthy|env_falsy|env_force_on|env_force_off|resolve_str|resolve_int)"
    r'\(\s*["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']',
)
INT_ENV = re.compile(
    r'_int_env\(\s*["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']',
)
TRUTHY_ENV = re.compile(
    r'_truthy_env\(\s*["\']((?:NIMBUSWARE|OLLAMA|PORT)[A-Z0-9_]*)["\']',
)

# Files allowed to read install vars before Postgres store is available.
BOOTSTRAP_REL = frozenset(
    {
        "env/settings_store.py",
        "env/dotenv.py",
        "env/admin_token.py",
        "env/edition.py",
        "env/run_app.py",
        "orchestrator/preflight_cli.py",
        "orchestrator/run_dispatch.py",
        "orchestrator/fleet_worker.py",
        "orchestrator/replay_cli.py",
        "orchestrator/routing_suggestions_cli.py",
        "orchestrator/telemetry_cli.py",
        "orchestrator/scraper_object_store.py",
        "orchestrator/ollama_manage.py",
        "orchestrator/llm/common.py",
        "memory/cli.py",
        "memory/sync_cli.py",
        "memory/embeddings.py",
        "extensions/bundle_memory_factory.py",
        "api/routes/runs/lifecycle.py",
        "maker/onboarding.py",
        "maker/session.py",
        "maker/cli.py",
        "env/admin_cli.py",
        "env/launcher_app.py",
        "env/desktop_common.py",
        "client/http.py",
        "orchestrator/runtime_bootstrap.py",
        "config/cli.py",
        "config/materializer.py",
        "api/app.py",
        "api/cli.py",
        "maker/store.py",
        "memory/factory.py",
        "memory/contribution.py",
        "memory/event_scan.py",
        "memory/remote_store.py",
        "memory/repo_scope.py",
        "research/enterprise_index.py",
        "api/routes/enterprise/fleet_memory.py",
        "console/config_materializer.py",
        "console/integrator_workflow_apply.py",
        "console/settings.py",
        "env/settings_resolve.py",
        "env/env_flags.py",
    },
)

# Managed keys may be written to os.environ only from the settings store sync.
ENV_WRITE_ALLOW = frozenset(
    {
        "env/settings_store.py",
        "env/dotenv.py",
        "env/admin_token.py",
        "env/run_app.py",
        "env/launcher_app.py",
        "orchestrator/preflight_cli.py",
        "scripts/install/install_nimbusware.py",
        "scripts/install/ollama_setup.py",
    },
)


def _rel(path: Path) -> str:
    return path.relative_to(PACKAGES).as_posix()


def audit(*, strict_writes: bool = True) -> list[str]:
    from env.settings_catalog import CATALOG, SettingScope

    errors: list[str] = []
    for py in sorted(PACKAGES.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = _rel(py)
        text = py.read_text(encoding="utf-8", errors="ignore")
        for pat in (ENV_GET, SETENV, ENV_HELPER, INT_ENV, TRUTHY_ENV):
            for m in pat.finditer(text):
                key = m.group(1)
                if key not in CATALOG:
                    errors.append(f"{rel}: unknown env key {key!r}")
                    continue
                scope = CATALOG[key].scope
                if rel not in BOOTSTRAP_REL and scope == SettingScope.INSTALL:
                    if pat in (ENV_GET, SETENV):
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
    from env.settings_catalog import CATALOG

    print(f"Operator env audit OK ({len(CATALOG)} catalog keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
