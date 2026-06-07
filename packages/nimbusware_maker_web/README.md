# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `static/js/tabs/home.js` | `/platform/readiness`, `/projects` |
| Build | `static/js/tabs/build.js` | `POST /runs` |
| Review | `static/js/tabs/review.js` | maker pending, research, stitch, slice diff, structured launch scorecard (rubric + LLM dimensions) |
| Progress | `static/js/tabs/progress.js` | theater + maker-progress SSE (includes `campaign_progress`), campaign pause/resume/cancel, memory-influence |
| Models | `static/js/tabs/models.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `static/js/tabs/settings.js` | `/settings/me`, hardware profile |
| Onboarding (wizard) | `static/js/tabs/wizard.js` | `/platform/onboarding` (first-run; run creation is on **Build**) |

Shared: `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js`, `tokens.css`.

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
