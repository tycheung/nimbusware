from __future__ import annotations

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended._factories import (
    _BOOL,
    _ENUM,
    _INT,
    _STR,
    _install,
)


def install_defs() -> tuple[SettingDef, ...]:
    return (
        _install("NIMBUSWARE_API_HOST", "API bind host", default="0.0.0.0"),
        _install(
            "NIMBUSWARE_UI",
            "Desktop UI mode",
            kind=_ENUM,
            default="maker",
            choices=("maker", "admin", "console"),
        ),
        _install("NIMBUSWARE_API_PORT", "API port override"),
        _install("NIMBUSWARE_MAKER_URL", "Maker URL", default="http://127.0.0.1:8501"),
        _install(
            "NIMBUSWARE_ADMIN_CONSOLE_URL", "Admin console URL", default="http://127.0.0.1:8502"
        ),
        _install("NIMBUSWARE_CONFIG_FROM_FILES", "Config from files only", kind=_BOOL, default="0"),
        _install(
            "NIMBUSWARE_COLLAB_ENABLED",
            "Collaborative chat (multi-user sessions)",
            kind=_BOOL,
            default="0",
        ),
        _install("NIMBUSWARE_CONFIG_NOTIFY", "Config NOTIFY pub/sub", kind=_BOOL, default="0"),
        _install(
            "NIMBUSWARE_ROLES_FROM_DB", "Roles registry from Postgres", kind=_BOOL, default="0"
        ),
        _install("NIMBUSWARE_FLEET_MEMORY_STORE_URI", "Fleet memory store URI"),
        _install("NIMBUSWARE_FLEET_MEMORY_STORE_DIR", "Fleet memory store directory"),
        _install(
            "NIMBUSWARE_OLLAMA_BASE_URL",
            "Canonical Ollama base URL",
            default="http://127.0.0.1:11434",
        ),
        _install("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", "Scraper object store URL"),
        _install("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "Scraper object store bucket"),
        _install(
            "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY",
            "Object store primary",
            kind=_BOOL,
            default="0",
        ),
        _install(
            "NIMBUSWARE_SCRAPER_ARTIFACT_LOCAL_MIRROR",
            "Mirror object-store scraper artifacts locally",
            kind=_BOOL,
            default="0",
        ),
        _install(
            "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_TIMEOUT_SECONDS",
            "Object store request timeout seconds",
            kind=_INT,
            default="30",
        ),
        _install(
            "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_DELETE_MAX_ATTEMPTS",
            "Max delete attempts for object-store prune",
            kind=_INT,
            default="1",
        ),
        _install(
            "NIMBUSWARE_HW_EXPECT_MIN_TIER",
            "Expected minimum hardware tier for fleet aggregate",
            kind=_STR,
            default="",
            choices=("", "weak", "standard", "strong"),
        ),
        _install(
            "NIMBUSWARE_REDIS_FLEET_URLS",
            "Redis fleet broker URLs",
            default="",
        ),
        _install("NIMBUSWARE_TENANT_ID", "Enterprise tenant id"),
        _install("NIMBUSWARE_MAKER_STATE_DIR", "Maker session state directory"),
        _install("NIMBUSWARE_HW_SSH_HOST", "Enterprise SSH hardware probe host"),
        _install("NIMBUSWARE_HW_SSH_IDENTITY", "SSH private key path for hardware probe"),
        _install(
            "NIMBUSWARE_HW_FLEET_HOSTS",
            "Comma-separated SSH hosts for fleet hardware tier aggregate",
        ),
        _install("NIMBUSWARE_WEBHOOK_SECRET", "External chat webhook HMAC secret"),
        _install("NIMBUSWARE_SANDBOX_K8S_EXEC_POD", "Fleet sandbox pod for kubectl exec"),
        _install("NIMBUSWARE_SANDBOX_K8S_NAMESPACE", "Fleet sandbox Kubernetes namespace"),
        _install("NIMBUSWARE_SANDBOX_K8S_WORKDIR", "Working directory inside fleet sandbox pod"),
        _install("NIMBUSWARE_E2B_API_KEY", "Enterprise E2B fleet sandbox API key"),
        _install("NIMBUSWARE_E2B_TEMPLATE", "Optional E2B sandbox template id"),
    )
