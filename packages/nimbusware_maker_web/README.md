# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `static/js/tabs/home.js` | `/platform/readiness`, `/projects` |
| Chat | `static/js/tabs/chat.js` | `/chat/sessions` (create, list, graph, fork, active-leaf), classify/start, inline theater SSE digest (`THEATER_CAP=12`; full theater on Progress) |
| Build | `static/js/tabs/build.js` | `POST /runs` (redirect banner to Chat) |
| Review | `static/js/tabs/review.js` | maker pending, research, stitch, slice diff, Run launch check + structured scorecard |
| Progress | `static/js/tabs/progress.js` + `progress/*` | theater + maker-progress SSE, ribbons, findings |
| Shared | `nimbusware_ui_shared` via `../../../nimbusware_ui_shared/` | api-core, formatters, launch-scorecard, theater-dom |
| Models | `static/js/tabs/models.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `static/js/tabs/settings.js` | `/settings/me`, hardware profile, **Run launch check** |
| Shared | `static/js/launch-scorecard.js` | Re-exports shared launch scorecard renderer |
| Onboarding (wizard) | `static/js/tabs/wizard.js` | `/platform/onboarding` (first-run; run creation is on **Build**) |

Shared: `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js`, `tokens.css`.

Operator UI shared modules: `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js`, `operator-default-profiles.js` (Progress + Chat ribbons and Settings default profiles).

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
