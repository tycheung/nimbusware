# Nimbusware API

FastAPI control plane for runs, timelines, bundles, config, and Enterprise IAM.

## Entry

- `poetry run nimbusware-api` — uvicorn on `HERMES_API_HOST` / `PORT`
- App factory: `nimbusware_api.app:app`

## Layout

| Area | Path |
|------|------|
| User routes | `routes/runs/`, `routes/bundles.py`, … |
| Admin / Enterprise | `routes/enterprise/` |
| Schemas + OpenAPI | `schemas/` |
| Timeline read models | `read_models/` (thin wrappers over `nimbusware_projections`) |
| Run list summary | `nimbusware_projections.run_summary` (`build_run_summary`) |

Errors use Problem+JSON (`nimbusware_api.errors.problem`). Edition gating via `nimbusware_env.edition`.
