# Nimbusware Maker

Server-side **maker approval** state machine and slice workflow helpers. The operator UI is the Alpine web app in [`nimbusware_maker_web`](../nimbusware_maker_web/README.md) at `/v1/maker/app/`.

## Entry

- `packages/nimbusware_maker/cli.py` — `poetry run nimbusware-maker` (starts API + web shell when configured)
- **Quick local mode:** `poetry run nimbusware-run --quick` — in-memory store, `quick_local` workflow; web shell shows a dismissible quick-mode banner
- API routes under `nimbusware_api/routes/runs/maker_*.py` implement plan/slice approval, pending state, git status, and workspace revert

## Web tabs (via `nimbusware_maker_web`)

| Tab | Role |
|-----|------|
| Home | Projects, readiness, intents, factory hero demos |
| **Chat** | Default entry — classify intent, start runs, session DAG fork/branch, inline theater digest (`chat.js`) |
| Build | Redirect banner to Chat; legacy `POST /runs` flow via API |
| Review | Pending slices, diff preview, research approve/reject, stitch summary, git commit status |
| Progress | Full run theater SSE, maker-progress SSE, operator ribbons, theater transcript export |
| Plan | Campaign backlog tree with surface badges, active slice highlight, maintenance countdown |
| Models | Ranked models, presets, Ollama pull, catalog-info strip |
| Settings | Operator settings, chat session resume toggle, hardware profile, per-discipline agent overlay editor |

First-run onboarding uses `GET /v1/platform/onboarding` (wizard tab in maker web).

## Layering

| Module | Role |
|--------|------|
| `slice_workflow/` | Approval orchestration (events, pending slice, revert) |
| `slice_engine.py` | **Sole** module-level import site for `nimbusware_orchestrator` slice execution |
| `deploy_credential_vault.py`, `deploy_pipeline_events.py`, `deploy_smoke.py`, `deploy_target_enforcement.py`, `terraform_validate.py` | Per-user deploy credentials + audit jsonl, validate/apply/smoke/rollback timeline stages, environment/target policy, and workspace Terraform helpers |
| `approval.py` | Read models from run events (pending, snapshots, git commits) |
| `workspace*.py` | Run workspace paths and snapshot restore |

Maker intentionally depends on the orchestrator for slice implement/verify/critique — that boundary is centralized in `slice_engine.py` and enforced by `test_maker_slice_workflow_uses_slice_engine_boundary`.

## Git outputs (per-slice commit)

When `NIMBUSWARE_SLICE_AUTO_COMMIT` is enabled, applying a slice that passes the gate runs `maybe_commit_slice` on the run workspace. The Review tab shows branch, short SHA, or skip reason via `GET /v1/runs/{id}/maker/git-status`; events include `git_commit` metadata on `slice.applied` stages.

HTTP to the API uses `NIMBUSWARE_API_BASE` and optional `NIMBUSWARE_API_KEY` / admin token headers from `nimbusware_client`.
