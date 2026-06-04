"""Catalog of operator-tunable environment variables by access grain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SettingScope(str, Enum):
    INSTALL = "install"
    SYSTEM = "system"
    USER = "user"
    RUN = "run"
    INTERNAL = "internal"


class SettingKind(str, Enum):
    BOOL = "bool"
    INT = "int"
    STR = "str"
    ENUM = "enum"


@dataclass(frozen=True)
class SettingDef:
    key: str
    scope: SettingScope
    kind: SettingKind
    default: str
    label: str
    description: str
    group: str
    choices: tuple[str, ...] = ()
    admin_editable: bool = True
    user_editable: bool = True


NS_OPERATOR_SETTINGS = "operator_settings"
KEY_SYSTEM = "system"
KEY_USER = "user"


def _defs() -> tuple[SettingDef, ...]:
    install = SettingScope.INSTALL
    system = SettingScope.SYSTEM
    user = SettingScope.USER
    run = SettingScope.RUN
    b = SettingKind.BOOL
    i = SettingKind.INT
    s = SettingKind.STR
    e = SettingKind.ENUM

    return (
        SettingDef(
            "NIMBUSWARE_DATABASE_URL",
            install,
            s,
            "",
            "Postgres URL",
            "Event store and config authority. Set in .env only.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_REPO_ROOT",
            install,
            s,
            "",
            "Repository root",
            "Path to Nimbusware install. Set in .env only.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_ADMIN_TOKEN",
            install,
            s,
            "",
            "Admin API token",
            "Secret for Admin Console and admin API routes. Set in .env only.",
            "Install — secrets",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_API_KEY",
            install,
            s,
            "",
            "Enterprise API key",
            "Enterprise Maker user key. Set in .env only.",
            "Install — secrets",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_EDITION",
            install,
            e,
            "individual",
            "Product edition",
            "individual or enterprise. Set at install.",
            "Install — infrastructure",
            choices=("individual", "enterprise"),
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_OIDC_ENABLED",
            install,
            b,
            "0",
            "OIDC SSO for consoles",
            "Enable enterprise Admin Console OIDC login gate.",
            "Install — enterprise SSO",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_OIDC_ISSUER",
            install,
            s,
            "",
            "OIDC issuer URL",
            "IdP issuer base URL (authorize/token endpoints under this host).",
            "Install — enterprise SSO",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_OIDC_CLIENT_ID",
            install,
            s,
            "",
            "OIDC client ID",
            "Registered OIDC client for Admin Console.",
            "Install — enterprise SSO",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_OIDC_CLIENT_SECRET",
            install,
            s,
            "",
            "OIDC client secret",
            "Optional for PKCE public clients.",
            "Install — secrets",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_AUDIT_RETENTION_DAYS",
            install,
            i,
            "90",
            "Audit retention days",
            "Default window for enterprise SOC2-oriented audit export.",
            "Install — enterprise audit",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_OIDC_REDIRECT_URI",
            install,
            s,
            "",
            "OIDC redirect URI",
            "Callback URL registered with IdP (defaults from NIMBUSWARE_ADMIN_CONSOLE_URL).",
            "Install — enterprise SSO",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_API_BASE",
            install,
            s,
            "http://127.0.0.1:8000/v1",
            "API base URL",
            "Maker/Admin → API URL. Set in .env only.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_UI_BACKEND",
            install,
            s,
            "web",
            "Desktop UI backend",
            "web = pywebview opens /v1/maker/app or /v1/admin/app (default).",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "PORT",
            install,
            s,
            "8000",
            "API port",
            "Uvicorn listen port for nimbusware-api.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "HERMES_SKIP_PREFLIGHT",
            system,
            b,
            "0",
            "Skip Ollama preflight",
            "Skip model preflight on run start (dev/CI).",
            "System — runtime",
        ),
        SettingDef(
            "HERMES_USE_LLM",
            user,
            b,
            "0",
            "Enable LLM stages",
            "Turn on Ollama-backed plan, critiques, and slice implement.",
            "User — maker runtime",
        ),
        SettingDef(
            "HERMES_SLICE_BUDGET_PRESET",
            user,
            e,
            "standard",
            "Slice budget preset",
            "tiny, standard, or careful — maps to max_files, max_loc, replan max.",
            "User — maker runtime",
            choices=("tiny", "standard", "careful"),
        ),
        SettingDef(
            "HERMES_SLICE_AUTO_ADVANCE",
            user,
            b,
            "1",
            "Auto-advance slices",
            "When off, pause for plan/slice approval in Maker.",
            "User — maker runtime",
        ),
        SettingDef(
            "HERMES_SLICE_IMPLEMENT",
            user,
            e,
            "scoped",
            "Slice implement mode",
            "scoped, stub, agent, or llm.",
            "User — maker runtime",
            choices=("scoped", "stub", "agent", "llm"),
        ),
        SettingDef(
            "HERMES_FILESYSTEM_JAIL",
            user,
            b,
            "1",
            "Agent tools filesystem jail",
            "Deny .env, .git, secrets paths; require scoped grep.",
            "User — agent tools safety",
        ),
        SettingDef(
            "HERMES_SLICE_E2E_COMMAND",
            user,
            e,
            "",
            "Slice E2E command",
            "Shell command for slice.e2e when workflow enables e2e.",
            "User — maker runtime",
        ),
        SettingDef(
            "HERMES_SANDBOX_BACKEND",
            user,
            e,
            "none",
            "Agent shell sandbox backend",
            "none runs locally; stub tags output; docker runs via docker run with workspace bind-mount.",
            "User — agent tools safety",
            choices=("none", "stub", "docker"),
        ),
        SettingDef(
            "HERMES_SANDBOX_DOCKER_IMAGE",
            user,
            e,
            "python:3.11-slim",
            "Docker image for agent shell sandbox",
            "Used when HERMES_SANDBOX_BACKEND=docker; workspace mounted at /workspace.",
            "User — agent tools safety",
        ),
        SettingDef(
            "HERMES_SLICE_AUTO_COMMIT",
            user,
            b,
            "0",
            "Git commit per slice",
            "Auto-commit after each passing slice gate.",
            "User — git outputs",
        ),
        SettingDef(
            "HERMES_GIT_NATIVE_OUTPUTS",
            user,
            b,
            "0",
            "Git finalize on run complete",
            "Commit when all slices pass gates.",
            "User — git outputs",
        ),
        SettingDef(
            "HERMES_GIT_PR_ON_COMPLETE",
            user,
            b,
            "0",
            "Open PR on complete",
            "Run gh pr create after final commit (requires gh CLI).",
            "User — git outputs",
        ),
        SettingDef(
            "HERMES_MICRO_SLICE_COUNT",
            run,
            i,
            "2",
            "Micro-slice count",
            "Max automatic slices per run (dev tuning).",
            "Run — slice loop",
        ),
        SettingDef(
            "HERMES_RERESARCH_MISSING_CONTEXT",
            system,
            b,
            "0",
            "Re-research on plan fail",
            "Bounded re-research when planner fails for missing context.",
            "System — research",
        ),
        SettingDef(
            "HERMES_RESEARCH",
            system,
            b,
            "0",
            "Research lane enabled",
            "Enable domain/code research stages when workflow allows.",
            "System — research",
        ),
        SettingDef(
            "HERMES_STITCH",
            system,
            b,
            "0",
            "Stitch lane enabled",
            "Enable transplant/stitch stages when workflow allows.",
            "System — research",
        ),
        SettingDef(
            "HERMES_PARALLEL_WRITERS",
            system,
            b,
            "0",
            "Parallel writers",
            "Run writer stages concurrently when workflow enables.",
            "System — pipeline",
        ),
        SettingDef(
            "HERMES_RUN_DISPATCH",
            install,
            e,
            "",
            "Run dispatch mode",
            "in-memory or redis. Infrastructure .env.",
            "Install — infrastructure",
            choices=("", "in-memory", "redis"),
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "HERMES_REDIS_URL",
            install,
            s,
            "",
            "Redis URL",
            "Fleet worker queue when dispatch=redis.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_CONFIG_FROM_DB",
            install,
            b,
            "1",
            "Config from Postgres",
            "Use Postgres config documents vs files only.",
            "Install — infrastructure",
            admin_editable=False,
            user_editable=False,
        ),
        SettingDef(
            "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE",
            user,
            s,
            "micro_slice",
            "Default workflow profile",
            "Default profile for new projects/runs in Maker.",
            "User — maker runtime",
        ),
        SettingDef(
            "NIMBUSWARE_MAX_SYSTEM_RAM_PCT",
            user,
            i,
            "75",
            "Max system RAM %",
            "Resource governor cap (also in Maker hardware settings).",
            "User — hardware governor",
        ),
        SettingDef(
            "NIMBUSWARE_HW_AUTO_ADJUST",
            user,
            b,
            "1",
            "Auto-adjust to hardware",
            "Adjust slice budgets from detected hardware tier.",
            "User — hardware governor",
        ),
        SettingDef(
            "HERMES_RUN_BANDIT",
            system,
            b,
            "0",
            "Run Bandit on verify",
            "Security scan with bandit during verify.",
            "System — verifiers",
        ),
        SettingDef(
            "HERMES_RUN_SEMGREP",
            system,
            b,
            "1",
            "Run Semgrep on verify",
            "Security scan with semgrep during verify.",
            "System — verifiers",
        ),
        SettingDef(
            "HERMES_RUN_PERF_SCAN",
            system,
            b,
            "1",
            "Run perf scan",
            "Lightweight performance scan during verify.",
            "System — verifiers",
        ),
        SettingDef(
            "HERMES_AGENT_EVALUATOR",
            system,
            b,
            "",
            "Agent evaluator",
            "Enable agent evaluator stage after verify (empty = YAML).",
            "System — optional stages",
        ),
        SettingDef(
            "HERMES_THEATER_LLM_SUMMARY",
            system,
            b,
            "",
            "Theater LLM summary",
            "Enable optional one-line LLM paraphrase for theater messages (off by default).",
            "System — theater",
        ),
        SettingDef(
            "HERMES_EMIT_INTEGRATOR_GATE",
            system,
            b,
            "",
            "Integrator gate",
            "Emit integrator gate decision stage (empty = YAML).",
            "System — optional stages",
        ),
        SettingDef(
            "HERMES_INTEGRATOR_MIN_SCORE_TO_PASS",
            system,
            s,
            "",
            "Integrator min score",
            "Override integrator pass threshold (empty = YAML).",
            "System — optional stages",
        ),
        SettingDef(
            "HERMES_INTEGRATOR_DEP_PREFLIGHT",
            system,
            b,
            "",
            "Integrator dep preflight",
            "Emit finding when bundle required_packages are missing from pyproject.",
            "System — optional stages",
        ),
        SettingDef(
            "HERMES_SELF_REFINEMENT_STAGE_MARKER",
            system,
            b,
            "0",
            "Self-refinement marker",
            "Emit self-refinement loop signals in timeline.",
            "System — optional stages",
        ),
        SettingDef(
            "HERMES_DEADLOCK_ESCALATION_MINUTES",
            system,
            i,
            "",
            "Deadlock escalation minutes",
            "Minutes before anti-deadlock escalation (empty = default).",
            "System — pipeline",
        ),
        SettingDef(
            "HERMES_OUTBOUND_FETCH_ENABLED",
            system,
            b,
            "0",
            "Outbound fetch",
            "Allow scraper HTTP fetch for allowlisted roles.",
            "System — egress",
        ),
        SettingDef(
            "HERMES_ATTACH_SECURITY_SCAN_METADATA",
            system,
            b,
            "0",
            "Attach security scan metadata",
            "Attach security scan metadata on verify events.",
            "System — security",
        ),
        SettingDef(
            "HERMES_UNANIMOUS_GATE_ENFORCE",
            system,
            b,
            "1",
            "Unanimous gate enforce",
            "Require unanimous gate pass (global override).",
            "System — gates",
        ),
        SettingDef(
            "HERMES_STUB_IMPLEMENTATION_CRITICS",
            system,
            b,
            "",
            "Stub implementation critics",
            "Force stub implementation critique panels (empty = YAML).",
            "System — critics",
        ),
    )


def _all_defs() -> tuple[SettingDef, ...]:
    from nimbusware_env.settings_catalog_extended import extended_defs

    merged: dict[str, SettingDef] = {}
    for d in _defs() + extended_defs():
        merged[d.key] = d
    return tuple(merged[k] for k in sorted(merged))


CATALOG: dict[str, SettingDef] = {d.key: d for d in _all_defs()}


def catalog_for_scope(scope: SettingScope) -> list[SettingDef]:
    return [d for d in CATALOG.values() if d.scope == scope]


def catalog_groups(scope: SettingScope | None = None) -> dict[str, list[SettingDef]]:
    out: dict[str, list[SettingDef]] = {}
    for d in CATALOG.values():
        if scope is not None and d.scope != scope:
            continue
        out.setdefault(d.group, []).append(d)
    for items in out.values():
        items.sort(key=lambda x: x.key)
    return dict(sorted(out.items()))
