# Common environment variables

Install-only variables: [`.env.example`](../.env.example). Runtime tunables in Postgres: [operator-settings.md](../operator-settings.md) (246-key catalog).

Resolve via `packages/env/env_flags.py` helpers (`env_flag_bool`, `env_str`, `env_tri_state`, …) — not raw `os.environ` in feature code.

| Variable | Scope | Purpose |
|----------|-------|---------|
| `NIMBUSWARE_DATABASE_URL` | install | Postgres for events + config |
| `NIMBUSWARE_REPO_ROOT` | install | Repo root for configs and artifacts |
| `NIMBUSWARE_ADMIN_TOKEN` | install | Admin Console + admin API |
| `NIMBUSWARE_API_BASE` | install | UI → API URL |
| `NIMBUSWARE_EDITION` | install | `individual` or `enterprise` |
| `NIMBUSWARE_USE_LLM` | user | Enable LLM-backed stages |
| `NIMBUSWARE_SLICE_AUTO_ADVANCE` | user | Auto-advance micro-slices |
| `NIMBUSWARE_FILESYSTEM_JAIL` | user | Deny secrets paths for agent tools |
| `NIMBUSWARE_SANDBOX_BACKEND` | user | `none`, `stub`, `docker`, `kubernetes`, `e2b` |
| `NIMBUSWARE_FAST_SLICE` | user | Skip optional critics when severity low |
| `NIMBUSWARE_SLICE_BUDGET_PRESET` | user | `tiny`, `standard`, or `careful` |
| `NIMBUSWARE_SLICE_E2E_COMMAND` | user | Custom browser verify command |
| `NIMBUSWARE_RUN_DISPATCH` | install | `memory` or `redis` for campaign worker |
| `NIMBUSWARE_REDIS_URL` | install | Redis for fleet dispatch |
| `NIMBUSWARE_OIDC_ENABLED` | install | Enterprise Admin OIDC SSO |
| `NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE` | user | Default workflow profile |

Audit catalog coverage: `poetry run python scripts/ci/audit_operator_env.py`

Context-efficiency flags: [context-efficiency.md](context-efficiency.md).
