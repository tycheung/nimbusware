# Nimbusware API

FastAPI control plane for runs, timelines, bundles, config, and Enterprise IAM.

## Entry

- `poetry run nimbusware-api` — uvicorn on `NIMBUSWARE_API_HOST` / `PORT`
- App factory: `api.app:app`
- Lifespan builds store/orchestrator via `orchestrator.runtime_bootstrap` (IAM/project stores stay in `app.py`).

## Dependencies

FastAPI route injection uses typed providers in `deps.py` (`EventStore`, `RunOrchestrator`, IAM/project stores).

## Layout

| Area | Path |
|------|------|
| User routes | `routes/runs/`, `routes/chat.py`, `routes/bundles.py`, `routes/ollama.py`, … |
| Integrations | `routes/integrations.py` — external chat webhook (complements Maker Chat; see `docs/integrations-external-chat.md`) |
| Admin / Enterprise | `routes/enterprise/`, `routes/admin_ui_bff.py` (Preact BFF, incl. `/admin/ui/enterprise/fleet-dashboard`) |
| Schemas + OpenAPI | `schemas/` |
| Timeline read models | `read_models/` (thin wrappers over `projections`) |
| Run list summary | `projections.run_summary` (`build_run_summary`) |

Errors use Problem+JSON (`api.errors.problem`). Edition gating via `env.edition`.

### Ollama model management

| Method | Path | Access |
|--------|------|--------|
| `GET` | `/platform/ollama/models` | User |
| `POST` | `/platform/ollama/pull` | User if `ollama_user_policy.allow_pull` |
| `DELETE` | `/platform/ollama/models/{name}` | User if `allow_delete` |
| `PATCH` | `/platform/ollama/routing/primary` | User if `allow_update_routing` |
| `PATCH` | `/admin/ollama/user-policy` | Admin |
| `POST` | `/admin/ollama/pull` | Admin |
| `DELETE` | `/admin/ollama/models/{name}` | Admin |

Policy defaults live in `configs/model-routing.yaml` (`ollama_user_policy`). Implementation: `orchestrator.routing.manage`, `ollama_user_policy`; persistence via `config.persist`.
