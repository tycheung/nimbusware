# Nimbusware Maker

Streamlit **user loop** for micro-slice workflows: plan approval, slice preview/apply, workspace snapshots, and revert.

## Entry

- `packages/nimbusware_maker/cli.py` — `poetry run nimbusware-maker`
- API routes under `nimbusware_api/routes/runs/maker_*.py` drive the same approval state machine server-side.

## Layering

| Module | Role |
|--------|------|
| `slice_workflow.py` | Approval UX orchestration (events, pending slice, revert) |
| `slice_engine.py` | **Sole** module-level import site for `hermes_orchestrator` slice execution |
| `api_client.py` | HTTP via `nimbusware_client` (no direct `httpx`) |
| `workspace*.py` | Run workspace paths and snapshot restore |

Maker intentionally depends on the orchestrator for slice implement/verify/critique — that boundary is centralized in `slice_engine.py` and enforced by `test_maker_slice_workflow_uses_slice_engine_boundary`.

HTTP to the API uses `NIMBUSWARE_API_BASE` and optional `NIMBUSWARE_API_KEY` / admin token headers from `nimbusware_client`.
