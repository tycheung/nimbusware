# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `static/js/tabs/home.js` | `/platform/readiness`, `/projects` |
| Build | `static/js/tabs/build.js` | `POST /runs` |
| Review | `static/js/tabs/review.js` | maker pending, research, slice diff, workspace revert (gate detail includes e2e skip reason when applicable) |
| Progress | `static/js/tabs/progress.js` | theater + maker-progress SSE, memory-influence (slice gate shows `slice.e2e` **SKIP** when browser verify is disabled or Playwright is unavailable) |
| Models | `static/js/tabs/models.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `static/js/tabs/settings.js` | `/settings/me`, hardware profile |
| Wizard | `static/js/tabs/wizard.js` | `/platform/onboarding` |

Shared: `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js`, `tokens.css`.

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
