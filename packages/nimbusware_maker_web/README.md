# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `home.js` + `home_readiness_ui.js`, `safe-coding-wizard.js` | `/platform/readiness`, `/platform/hardware`, `/platform/workspace-*`, `/platform/playwright-bootstrap`, `/projects` |
| Chat | `chat.js` + `chat_session_lifecycle.js`, `chat_shell_html.js`, `chat_run_card_ui.js`, `chat_collab_wiring.js`, `chat_model_drawer_ui.js`, `chat_invite_modal_ui.js`, `chat_*_ui.js` | `/chat/sessions` (create, list, graph, fork, active-leaf), classify/start, inline theater SSE digest (`THEATER_CAP=12`; full theater on Progress) |
| Build | `static/js/tabs/build.js` | `POST /campaigns` (banner redirects operators to Chat for new work) |
| Review | `review.js` + `review_*_ui.js` | maker pending, research, stitch, slice diff, Run launch check + structured scorecard; enterprise audit export link |
| Progress | `static/js/tabs/progress.js` + `progress/*` (`render-chips.js`, `progress_status_chips.js`, `operator-ribbons.js`, `progress_ribbon_refresh.js`) | theater + maker-progress SSE, ribbons, findings |
| Models | `models.js` + `models_local_ui.js`, `models_ollama_ui.js`, `models_*_ui.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `settings.js` + `settings_shell_html.js`, `settings_governor_ui.js`, `settings_*_ui.js` | `/settings/me`, hardware profile, **Run launch check**, **collab toggle** (`/platform/collab-settings`) |
| Onboarding (wizard) | `static/js/tabs/wizard.js` | `/platform/onboarding` (first-run; run creation is on **Build** or **Chat**) |

## Shared modules

| Module | Role |
|--------|------|
| `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js` | Shell, routing, API |
| `archetype-picker.js` | First-run Safe Coding vs Engineer preset |
| `operator-default-profiles.js` | Default autopilot/enforcement/workflow ids |
| `interjection-ribbon.js`, `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js` | Progress + Chat operator ribbons |
| `launch-scorecard.js` | Re-exports shared launch scorecard renderer |
| `nimbusware_ui_shared` via `../../../nimbusware_ui_shared/` | api-core, formatters, launch-scorecard, theater-dom |

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
