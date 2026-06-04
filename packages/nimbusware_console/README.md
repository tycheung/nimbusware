# Nimbusware Admin Console (backend)

Python **admin/dev control plane** for inspecting runs, editing repo config, and driving operator workflows. The browser UI is the Preact app in [`nimbusware_admin_ui`](../nimbusware_admin_ui/) served at `/v1/admin/app/`. End users should use [`nimbusware_maker`](../nimbusware_maker/README.md) at `/v1/maker/app/`.

## Running

| Entry | Command |
|-------|---------|
| Admin web UI | `nimbusware-admin` or `nimbusware-run --admin` (opens `/v1/admin/app/` via pywebview when `NIMBUSWARE_UI_BACKEND=web`) |
| API only | `poetry run nimbusware-api` then open `http://127.0.0.1:8000/v1/admin/app/` |

Build the Admin SPA before packaging: `cd packages/nimbusware_admin_ui && npm ci && npm run build` (commit `dist/` or ship in release artifacts).

### Environment

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_REPO_ROOT` | Frozen repo root for local YAML reads (catalog, personas, workflows) |
| `NIMBUSWARE_API_BASE` | API base for run list, detail, timeline, findings |
| `NIMBUSWARE_ADMIN_TOKEN` | Admin gate (`X-Nimbusware-Admin-Token`) |
| `NIMBUSWARE_UI_BACKEND` | `web` (default; pywebview opens `/v1/admin/app/`) |

Repo root and API base helpers live in `settings.py` (`repo_root()`, `API_BASE`).

## Package layout

```
nimbusware_console/
├── services/              # HTTP clients to /v1 (run list, chat, config, …)
├── *_display.py           # Authoritative formatters for timeline/findings/critic panels
├── operator_chat_core.py  # Operator chat command handling (BFF: POST /v1/admin/ui/operator-chat/message)
├── admin_gate.py          # Token gate helpers
├── integrator_gate/       # Integrator gate display logic
└── enterprise_console*.py # Enterprise fleet formatters (Admin Fleet tab at /v1/admin/app/fleet)
```

Admin UX lives in `nimbusware_admin_ui` (Metrics, Preflight, Runs, …) and reuses the display modules above via API BFF routes.

## Tests

Console display helpers: `tests/console/test_console_*.py`. Admin BFF: `tests/api/test_admin_ui_bff.py`.
