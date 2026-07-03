from __future__ import annotations

from env.settings_catalog import SettingDef
from env.settings_catalog_extended._factories import (
    _BOOL,
    _ENUM,
    _INT,
    _STR,
    _internal,
)


def internal_defs() -> tuple[SettingDef, ...]:
    return (
        _internal("NIMBUSWARE_WORKSPACE", "Dev workspace path override"),
        _internal(
            "NIMBUSWARE_WORKFLOW_PROFILE",
            "Legacy workflow profile alias (deprecated)",
            kind=_STR,
        ),
        _internal(
            "OLLAMA_HOST",
            "Legacy Ollama URL alias (prefer NIMBUSWARE_OLLAMA_BASE_URL)",
            default="http://127.0.0.1:11434",
        ),
        _internal("PORT", "Legacy API port alias (prefer NIMBUSWARE_API_PORT)", default="8000"),
        _internal("NIMBUSWARE_REFACTOR_FORCE_FAIL", "Force refactor stage fail", kind=_BOOL),
        _internal("NIMBUSWARE_REFACTOR_STAGE", "Refactor stage override"),
        _internal(
            "NIMBUSWARE_PARALLEL_WRITER_TEST_DELAY_SECONDS", "Parallel writer test delay", kind=_INT
        ),
        _internal(
            "NIMBUSWARE_HW_FIXTURE",
            "Hardware profile fixture",
            kind=_ENUM,
            choices=("weak", "medium", "strong"),
        ),
        _internal("NIMBUSWARE_HW_SSH_MOCK", "Mock SSH hardware probe", kind=_BOOL),
        _internal(
            "NIMBUSWARE_PRESSURE_DEGRADE_STUB", "Degrade LLM to stub under RAM block", kind=_BOOL
        ),
        _internal("GITHUB_TOKEN", "GitHub Actions token for external CI check-runs"),
        _internal("GITLAB_TOKEN", "Legacy GitLab token alias (prefer NIMBUSWARE_GITLAB_TOKEN)"),
        _internal("NIMBUSWARE_CI_GITHUB_REPO", "CI GitHub repo slug"),
        _internal("NIMBUSWARE_CI_HEAD_SHA", "CI head SHA"),
        _internal("NIMBUSWARE_GITLAB_TOKEN", "GitLab API token for external CI"),
        _internal("NIMBUSWARE_CI_GITLAB_PROJECT", "GitLab project id or namespace/project"),
        _internal("NIMBUSWARE_GITLAB_API_BASE", "GitLab API base URL"),
        _internal("NIMBUSWARE_TIMELINE_BASE_URL", "Timeline base URL for CI"),
        _internal("NIMBUSWARE_FLEET_OLLAMA_SLI_BASE_URL", "Fleet Ollama SLI base URL"),
        _internal("NIMBUSWARE_FLEET_OLLAMA_SLI_EXPORT_PATH", "Fleet Ollama SLI export path"),
        _internal("NIMBUSWARE_FLEET_OLLAMA_SLI_HEALTH_PATH", "Fleet Ollama SLI health path"),
        _internal("NIMBUSWARE_WORKSPACE_SNAPSHOT_DIR", "Workspace snapshot directory"),
        _internal("NIMBUSWARE_MEMORY_INDEX_DIR", "Memory index directory"),
        _internal("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", "Scraper artifact directory"),
        _internal("NIMBUSWARE_PRUNE_STATUS_PATH", "Prune status export path"),
        _internal("NIMBUSWARE_SQL_QUERY_COUNT_MAX", "SQL query count max", kind=_INT),
        _internal("NIMBUSWARE_TEST_SQL_QUERY_COUNT", "Test SQL query count flag", kind=_BOOL),
        _internal("NIMBUSWARE_TEST_WRITER_STAGE_CMD", "Test writer stage command override"),
        _internal("NIMBUSWARE_QUICK_MODE", "Quick mode bootstrap", kind=_BOOL),
        _internal(
            "NIMBUSWARE_FACTORY_EXPLORATORY_CRAWL",
            "Enable exploratory Playwright ISM crawl on factory T3",
            kind=_BOOL,
        ),
        _internal(
            "NIMBUSWARE_FACTORY_EXPLORATORY_MAX_CLICKS",
            "Max Playwright navigations during factory exploratory ISM crawl",
            kind=_INT,
        ),
        _internal(
            "NIMBUSWARE_FACTORY_EXPLORATORY_MAX_DEPTH",
            "Max link depth during factory exploratory ISM crawl",
            kind=_INT,
        ),
        _internal("NIMBUSWARE_PUT_SANDBOX", "PUT preview sandbox mode (docker)"),
        _internal(
            "NIMBUSWARE_DEV_ENV_ENABLED", "Enable persistent dev environment supervisor", kind=_BOOL
        ),
        _internal(
            "NIMBUSWARE_DEV_ENV_PORT_BASE", "Base port for dev env session allocation", kind=_INT
        ),
        _internal(
            "NIMBUSWARE_DEV_ENV_BASE_URL", "Attach to external dev server instead of spawning"
        ),
        _internal("NIMBUSWARE_PUT_BASE_URL", "External PUT preview base URL override"),
        _internal(
            "NIMBUSWARE_ALLOW_WORKFLOW_YAML_WRITE",
            "Allow integrator workflow YAML write from console",
            kind=_BOOL,
            default="0",
        ),
        _internal(
            "NIMBUSWARE_OIDC_MOCK",
            "Mock OIDC admin sign-in (dev only)",
            kind=_BOOL,
            default="0",
        ),
        _internal(
            "NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK",
            "Mock desktop subscription OAuth (dev/tests only)",
            kind=_BOOL,
            default="0",
        ),
        _internal(
            "NIMBUSWARE_OIDC_ADMIN_GROUPS",
            "Comma-separated IdP groups granting Admin console write access",
        ),
        _internal(
            "NIMBUSWARE_OIDC_MOCK_GROUPS",
            "Mock OIDC groups claim for dev SSO (default nimbusware-admins)",
        ),
        _internal(
            "NIMBUSWARE_UI_CONTROLLER_ENABLED", "Enable UI controller regression", kind=_BOOL
        ),
        _internal(
            "NIMBUSWARE_LAUNCH_TEST_ENABLED",
            "Enable launch-test writer/critic stages on full-stack profiles",
            kind=_BOOL,
        ),
        _internal(
            "NIMBUSWARE_LAUNCH_TEST_STUB",
            "Stub unknown launch_test stages (tests only)",
            kind=_BOOL,
        ),
        _internal(
            "NIMBUSWARE_LAUNCH_TEST_WRITER_MODEL",
            "Ollama model for launch-test UI flow writer (empty = ISM synthesis only)",
            kind=_STR,
        ),
        _internal(
            "NIMBUSWARE_DEV_ENV_MILESTONES_BYPASS",
            "Skip M1–M6 gating for dev-env auto-start and regression",
            kind=_BOOL,
        ),
        _internal(
            "NIMBUSWARE_HUMAN_FIDELITY_ENABLED",
            "Run human-fidelity suite before slice gate when dev env is up",
            kind=_BOOL,
        ),
        _internal(
            "NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_URL",
            "S3-compatible URL for factory evidence zip mirror",
        ),
        _internal(
            "NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_BUCKET",
            "Bucket for factory evidence object store",
        ),
        _internal("NIMBUSWARE_MAKER_VAPID_PRIVATE_KEY", "Maker Web Push VAPID private key"),
        _internal("NIMBUSWARE_MAKER_VAPID_SUBJECT", "Maker Web Push VAPID subject (mailto:)"),
        _internal(
            "NIMBUSWARE_MAKER_PUSH_SUBSCRIPTIONS_FILE",
            "Path to persisted push subscription JSON",
        ),
        _internal("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", "Fleet Playwright WS endpoint"),
        _internal("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY", "Maker Web Push VAPID public key"),
        _internal("NIMBUSWARE_DATA_DIR", "Nimbusware data directory root"),
        _internal(
            "NIMBUSWARE_SWE_BENCH_WRITE_JSON",
            "Write micro_slice regression harness JSON snapshot",
            kind=_BOOL,
            default="0",
        ),
        _internal(
            "NIMBUSWARE_E2E_FLAKE_RETRIES",
            "E2E pytest reruns for flake budget",
            kind=_INT,
            default="0",
        ),
        _internal(
            "NIMBUSWARE_E2E_FLAKE_DELAY",
            "Delay seconds between E2E reruns",
            kind=_INT,
            default="2",
        ),
        _internal("NIMBUSWARE_CAMPAIGN_SOAK_JOURNEYS", "Campaign soak journey module list"),
        _internal(
            "NIMBUSWARE_CAMPAIGN_SOAK_PASSES",
            "Campaign soak pass count",
            kind=_INT,
            default="2",
        ),
        _internal(
            "NIMBUSWARE_FRAMEWORK_PACK_FIDELITY",
            "Enable keyboard/mouse fidelity in framework pack CI gate",
            kind=_BOOL,
            default="0",
        ),
    )
