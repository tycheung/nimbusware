# nimbusware_admin_ui

Preact + Vite Admin SPA served at `/v1/admin/app` (Enterprise fleet at `/fleet`).

## Build

```bash
cd packages/nimbusware_admin_ui
npm ci
npm run build
```

Local `scripts/ci_check.ps1` runs `npm run build` then vitest before Playwright.

Deep links such as `/v1/admin/app/runs/{id}` are served via SPA fallback (`AdminSPAStaticFiles` in `nimbusware_api.routes.admin_web`); the Preact router strips the `/v1/admin/app` prefix client-side.

## Tests

```bash
npm test
```

## Campaign run detail

For `workflow_profile=campaign_micro_slice`, `RunDetailPage` loads:

- `GET /v1/campaigns/{run_id}/progress` — progress, backlog tree, maintenance events

Panels: `CampaignProgressPanel`, `BacklogTreePanel`, `MaintenanceEventsPanel`.

## Launch eval

`RunDetailPage` includes `LaunchScorecardPanel` — loads `launch_eval.completed` from the run timeline, **Run launch check** via `POST /v1/runs/{id}/maker/launch-eval`, and optional LLM dimension rows when present on the scorecard metadata.

## BFF

Admin tables use `/v1/admin/ui/*` BFF routes; run detail uses `/v1/runs/*` and campaign routes above.
