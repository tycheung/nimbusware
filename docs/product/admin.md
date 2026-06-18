# Admin Console

**Admin/dev only** — not part of the default product path.

Web app: `GET /v1/admin/app/` ([`packages/nimbusware_admin_ui`](../../packages/nimbusware_admin_ui/)). Sign in with `NIMBUSWARE_ADMIN_TOKEN` (stored in `sessionStorage`).

Launch: `poetry run nimbusware-admin`, `nimbusware-run --admin`, or launcher **Admin Console** button.

After UI changes: `cd packages/nimbusware_admin_ui && npm ci && npm run build`

## Runs & timeline

- Filtered run list (workflow, dates, escalation, status), pagination, CSV/JSON export
- Run detail: summary, timeline, findings, critic matrix, theater panel, policy compare, probation notices
- Lifecycle: start, plan, verify, slice; escalate; override gate
- Campaign panels (when `campaign_micro_slice`): progress, backlog tree, maintenance events
- Research, stitch, integration adapter, factory evidence, launch scorecard panels
- **Open in Maker Review** deep link; per-run audit export download

## Configuration

- Ollama models — pull/delete, user policy toggles
- Operator chat — start runs, steer workflow
- Custom agents — CRUD + system prompt editor
- Bundle catalog search, FAISS status, catalog editor
- Persona shelves, workflow explainers, integrator preview
- Blast radius and critic packs config tabs
- Preflight trends and fleet metrics export

## Enterprise Fleet tab

`/v1/admin/app/fleet` — requires Enterprise API key at sign-in:

- Tenant switcher, fleet memory status
- Ollama SLI + preflight aggregate
- Redis worker health, hardware fleet tiers, rescan
- Cross-tenant gate comparison with CSV export

Preflight history remains on the **Preflight** tab.

## Analytics

- **Metrics** — `GET /v1/platform/analytics/competitive-summary`, bundle outcomes, chat-turn analytics
- **Hardware** — `GET /v1/platform/analytics/pressure-history`

Operator settings catalog: [operator-settings.md](../operator-settings.md).
