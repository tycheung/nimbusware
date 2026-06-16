# Nimbusware Env

Nimbusware platform edition, dotenv loading, admin token helpers, and shared `NIMBUSWARE_*` env flag parsing for the Nimbusware online agentic system.

## Key modules

| Module | Purpose |
|--------|---------|
| `edition.py` | Individual vs Enterprise feature gates |
| `dotenv.py` | Repo-root `.env` discovery and `load_dotenv()` |
| `admin_token.py` | Default dev token + non-loopback bind guard |
| `env_flags.py` | Catalog-backed env reads (`nimbusware_database_url`, `nimbusware_repo_root_path`, `nimbusware_sandbox_backend`, `nimbusware_tenant_id`, `nimbusware_bundle_memory_rank_weight`, tri-state flags, URL helpers) |

Call `load_dotenv()` early in CLI entrypoints (`nimbusware-api`, desktop launcher). Production binds should set a non-default `NIMBUSWARE_ADMIN_TOKEN`; `require_non_default_admin_token_for_host()` blocks unsafe defaults off loopback.
