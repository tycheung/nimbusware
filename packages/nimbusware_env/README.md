# Nimbusware Env

Edition, dotenv loading, admin token helpers, and shared `HERMES_*` env flag parsing.

## Key modules

| Module | Purpose |
|--------|---------|
| `edition.py` | Individual vs Enterprise feature gates |
| `dotenv.py` | Repo-root `.env` discovery and `load_dotenv()` |
| `admin_token.py` | Default dev token + non-loopback bind guard |
| `env_flags.py` | Central truthy/falsey parsers for orchestrator and config flags |

Call `load_dotenv()` early in CLI entrypoints (`nimbusware-api`, desktop launcher). Production binds should set a non-default `NIMBUSWARE_ADMIN_TOKEN`; `require_non_default_admin_token_for_host()` blocks unsafe defaults off loopback.
