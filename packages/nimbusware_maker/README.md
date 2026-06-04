# Nimbusware Maker

Server-side **maker approval** state machine and slice workflow helpers. The operator UI is the Alpine web app in [`nimbusware_maker_web`](../nimbusware_maker_web/README.md) at `/v1/maker/app/`.

## Entry

- `packages/nimbusware_maker/cli.py` — `poetry run nimbusware-maker` (starts API + web shell when configured)
- **Quick local mode:** `poetry run nimbusware-run --quick` — in-memory store, `quick_local` workflow; web shell shows a dismissible quick-mode banner
- API routes under `nimbusware_api/routes/runs/maker_*.py` implement plan/slice approval, pending state, git status, and workspace revert

## Web tabs (via `nimbusware_maker_web`)

| Tab | Role |
|-----|------|
| Home | Projects, readiness, project create (delete via Admin console) |
| Build | Intent → `POST /runs` |
| Review | Pending slices, diff preview, research approve/reject, stitch summary, git commit status |
| Progress | Theater SSE, maker-progress SSE, theater transcript export |
| Models | Ranked models, presets, Ollama pull, catalog-info strip |
| Settings | Operator settings with catalog labels, hardware profile |

First-run onboarding uses `GET /v1/platform/onboarding` (wizard tab in maker web).

## Layering

| Module | Role |
|--------|------|
| `slice_workflow/` | Approval orchestration (events, pending slice, revert) |
| `slice_engine.py` | **Sole** module-level import site for `hermes_orchestrator` slice execution |
| `approval.py` | Read models from run events (pending, snapshots, git commits) |
| `workspace*.py` | Run workspace paths and snapshot restore |

Maker intentionally depends on the orchestrator for slice implement/verify/critique — that boundary is centralized in `slice_engine.py` and enforced by `test_maker_slice_workflow_uses_slice_engine_boundary`.

## Git outputs (per-slice commit)

When `HERMES_SLICE_AUTO_COMMIT` is enabled, applying a slice that passes the gate runs `maybe_commit_slice` on the run workspace. The Review tab shows branch, short SHA, or skip reason via `GET /v1/runs/{id}/maker/git-status`; events include `git_commit` metadata on `slice.applied` stages.

HTTP to the API uses `NIMBUSWARE_API_BASE` and optional `NIMBUSWARE_API_KEY` / admin token headers from `nimbusware_client`.
