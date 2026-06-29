# nimbusware_maker_web

Alpine.js Maker web app served at `/v1/maker/app/`.

## Tabs

| Tab | Module | APIs |
|-----|--------|------|
| Home | `home.js` + `home_readiness_ui.js`, `home_enterprise_policy_ui.js`, `safe-coding-wizard.js` | `/platform/readiness`, `/platform/fleet-governance`, workspace scaffold/precommit, Playwright bootstrap |
| Chat | `chat.js` + `chat_session_lifecycle.js`, `chat_shell_html.js`, `chat_solo_hat_ui.js`, `chat_run_card_ui.js`, `chat_collab_wiring.js`, `chat_model_drawer_ui.js`, `chat_invite_modal_ui.js`, `chat_mention_ui.js`, `chat_join.js`, `chat_*_ui.js` | `/chat/sessions`, classify/start, `@` routing, solo hat chips, join discipline picker, dev-env **Open preview** on run cards |
| Build | `static/js/tabs/build.js` | `POST /campaigns` (banner redirects operators to Chat for new work) |
| Plan | `static/js/tabs/plan.js` | `/campaigns/{id}/backlog`, `/runs/{id}/maker-progress` (active slice + maintenance), timeline for `slice.contract` gate |
| Review | `review.js` + `review_*_ui.js`, `deploy_cockpit.js` | maker pending, deploy cockpit (validate + approve), git/PR/CI status, scorecard |
| Progress | `static/js/tabs/progress.js` + `progress/*`, `deploy_cockpit.js` | theater SSE (severity + evidence), findings filter, completion cockpit + auto launch check, deploy cockpit, ribbons |
| Models | `models.js` + `models_local_ui.js`, `models_ollama_ui.js`, `models_*_ui.js` | `/platform/hardware`, `/platform/models/catalog-info`, Ollama pull |
| Settings | `settings.js` + `settings_shell_html.js`, `settings_governor_ui.js`, `settings_deploy_ui.js`, `settings_solo_discipline_ui.js`, `settings_safe_coding_ui.js`, `settings_*_ui.js` | `/settings/me`, hardware profile, **Run launch check**, **deploy connection labels**, **solo discipline hat**, industry critic packs (`/platform/industry-critic-packs`), **collab toggle** (`/platform/collab-settings`) |
| Onboarding (wizard) | `static/js/tabs/wizard.js` | `/platform/onboarding` (first-run; run creation is on **Build** or **Chat**) |

## Shared modules

| Module | Role |
|--------|------|
| `api-client.js`, `sse-client.js`, `app-shell.js`, `tab-loader.js` | Shell, routing, API |
| `archetype-picker.js` | First-run Safe Coding vs Engineer preset |
| `operator-default-profiles.js` | Default autopilot/enforcement/workflow ids |
| `interjection-ribbon.js`, `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js` | Progress + Chat operator ribbons (interjection prefix chips) |
| `deploy_cockpit.js`, `chat_mention_ui.js`, `chat_join.js` | Deploy cockpit (validate + approve); `@` discipline autocomplete + routing |
| `launch-scorecard.js` | Shared launch scorecard renderer + per-surface launch summary chips |
| `configs/workflows/safe_coding_campaign_fullstack.yaml` | Safe Coding + full-stack campaign merge (server-side) |
| `nimbusware_ui_shared` via `../../../nimbusware_ui_shared/` | api-core, formatters, launch-scorecard, theater-dom |

Mount: [`packages/nimbusware_api/routes/maker_web.py`](../nimbusware_api/routes/maker_web.py).

Vitest: `npm test` in this package.
