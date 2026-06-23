# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `home.js` + `home_readiness_ui.js` | `/platform/readiness`, `/platform/hardware`, `/projects` |
| Chat | `chat.js` + `chat_shell_html.js`, `chat_run_card_ui.js`, `chat_collab_wiring.js`, `chat_invite_modal_ui.js`, `chat_*_ui.js` | `/chat/sessions` (create, list, graph, fork, active-leaf), classify/start, inline theater SSE digest (`THEATER_CAP=12`; full theater on Progress) |
| Build | `static/js/tabs/build.js` | `POST /runs` (redirect banner to Chat) |
| Review | `review.js` + `review_*_ui.js` | maker pending, research, stitch, slice diff, Run launch check + structured scorecard |
| Progress | `static/js/tabs/progress.js` + `progress/*` (`render-chips.js`, `progress_status_chips.js`) | theater + maker-progress SSE, ribbons, findings |
| Shared | `nimbusware_ui_shared` via `../../../nimbusware_ui_shared/` | api-core, formatters, launch-scorecard, theater-dom |
| Models | `models.js` + `models_*_ui.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `settings.js` + `settings_shell_html.js`, `settings_governor_ui.js`, `settings_*_ui.js` | `/settings/me`, hardware profile, **Run launch check** |
| Shared | `static/js/launch-scorecard.js` | Re-exports shared launch scorecard renderer |
| Onboarding (wizard) | `static/js/tabs/wizard.js` | `/platform/onboarding` (first-run; run creation is on **Build**) |

Shared: `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js`, `tokens.css`.

Operator UI shared modules: `interjection-ribbon.js`, `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js`, `operator-default-profiles.js` (Progress + Chat ribbons and Settings default profiles).

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
