# Nimbusware Maker

Streamlit **user loop** for micro-slice workflows: plan approval, slice preview/apply, workspace snapshots, and revert.

## Simple vs Advanced

**Simple** is the default: plain-language progress, no operator telemetry. **Advanced** appears in the sidebar only after **Sign in as admin** (same machine); it shows extra diagnostics. Full ops tooling remains in the [Admin Console](../nimbusware_console/README.md).

## Entry

- `packages/nimbusware_maker/cli.py` — `poetry run nimbusware-maker`
- **Quick local mode:** `poetry run nimbusware-run --quick` (or `nimbusware-maker --quick` with API started in the same env) — in-memory store, `quick_local` workflow.
- API routes under `nimbusware_api/routes/runs/maker_*.py` drive the same approval state machine server-side.
- First-run wizard on Home when onboarding is not complete (folder → readiness smoke → intent → create run).

## Layering

| Module | Role |
|--------|------|
| `ui/` | Streamlit panels (home, build, review, progress, settings + Ollama models) |
| `services/` | Testable `/v1` helpers (e.g. `services/ollama.py`) without Streamlit |
| `slice_workflow/` | Approval UX orchestration (events, pending slice, revert) |
| `slice_engine.py` | **Sole** module-level import site for `hermes_orchestrator` slice execution |
| `api_client.py` | HTTP via `nimbusware_client` (no direct `httpx`) |
| `workspace*.py` | Run workspace paths and snapshot restore |

Maker intentionally depends on the orchestrator for slice implement/verify/critique — that boundary is centralized in `slice_engine.py` and enforced by `test_maker_slice_workflow_uses_slice_engine_boundary`.

HTTP to the API uses `NIMBUSWARE_API_BASE` and optional `NIMBUSWARE_API_KEY` / admin token headers from `nimbusware_client`.
