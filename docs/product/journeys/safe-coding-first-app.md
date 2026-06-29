# Safe Coding — first full-stack app

Build a todo app with web UI and REST API using the **Safe Coding** persona. Extra approval gates and plain-language progress; no terminal steps on Home.

## Prerequisites

1. Install with `--setup-bundle default` ([install-profiles.md](../../install-profiles.md)).
2. Open Maker and choose **Safe Coding** in the archetype picker.
3. Confirm **Home** readiness is green (or run **Prepare workspace**).

## Journey steps

### 1. Prepare workspace (Home)

Use the first-run **Prepare workspace** panel:

- `GET /v1/platform/workspace-readiness`
- `POST /v1/platform/workspace-scaffold` — adds smoke tests when missing
- `POST /v1/platform/workspace-precommit`
- `POST /v1/platform/playwright-bootstrap` — poll until `ready`

See [safe-coding.md](../safe-coding.md) for API details.

### 2. Start discovery (Chat)

1. Click **Build full-stack app** on Home (or Home intent **Build an app**).
2. In Chat, enter: *Build a todo app with web UI and API*.
3. Work type routes to **campaign** → `safe_coding_campaign_fullstack`.
4. Answer scope discovery chips; use **Explain** on any question you are unsure about.
5. Tap **Recommend for me** if you prefer defaults, or confirm each field manually.
6. Read the manifest approval card and click **Approve manifest**.

### 3. Watch delivery (Progress)

- Surface-aware slice headlines (Web UI, API, Contract).
- Plain-language gate summaries instead of raw stage ids.
- Guided autopilot pauses on gate failures — review before continuing.
- Optional industry critic pack in Settings (`fintech-api`, `healthcare-api`).

### 4. Review and ship (Review)

- Approve slices when prompted.
- Run **launch check** when the campaign completes.
- Export audit bundle if needed: `GET /v1/runs/{id}/audit-export`.

## What differs from Engineer workspace

| Control | Safe Coding |
|---------|-------------|
| Workflow | `safe_coding_campaign_fullstack` |
| Autopilot | `guided` — pauses on failures |
| Collab | Off by default |
| Home wizard | Zero-terminal scaffold + Playwright bootstrap |

## Next steps

- [maker.md](../maker.md) — tabs and operator ribbons
- [engineer-first-app.md](engineer-first-app.md) — team collab and solo hat routing
