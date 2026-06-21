# Model Hub

Maker **Models** tab (`#/models`, `data-testid="maker-model-hub"`) is the operator surface for local Ollama and cloud API connections (v1.2 Track C).

## Sections

### Local models (`#/models?section=local`)

- Ollama reachability badge and **Install Ollama** (`POST /v1/platform/ollama/bootstrap`)
- Installed models from `GET /v1/platform/ollama/models` — pull update, delete
- Manual pull form and ranked preset wizard (unchanged from v1.1)
- Hardware strip and GPU pool filters for ranked catalog

### API connections (`#/models?section=api-connections`)

- Provider cards from `GET /v1/platform/provider-presets` (Ollama, OpenAI, Anthropic Messages API, Google Gemini OpenAI-compat, Grok, OpenRouter, custom)
- Per-user vault via `PUT /v1/platform/provider-connections` (secrets encrypted in Postgres)
- **Test** runs `POST /v1/platform/provider-connections/{id}/probe`
- Subscription-style providers (ChatGPT Plus, Claude Pro) use a local “connected via app” flag — no host-side OAuth

### Cursor card

Static explainer: Cursor Composer is IDE-only; use [`docs/ide-bridge.md`](ide-bridge.md).

## Home integration

Readiness actions `start_ollama` / `pull_model` deep-link to Model Hub instead of terminal toasts. Barebones install profile shows a Model Hub CTA on Home.

## Gitops

`nimbusware-config export` writes `configs/provider_connections/metadata.yaml` with connection metadata only — **no API keys**.

## API summary

| Method | Path |
|--------|------|
| GET | `/v1/platform/provider-presets` |
| GET | `/v1/platform/provider-connections` |
| PUT | `/v1/platform/provider-connections` |
| DELETE | `/v1/platform/provider-connections/{connection_id}` |
| POST | `/v1/platform/provider-connections/{connection_id}/probe` |
| POST | `/v1/platform/ollama/bootstrap` |
| POST | `/v1/runs/{run_id}/model-bindings/swap` |
| POST | `/v1/chat/sessions/{id}/model-bindings/swap` |
| POST | `/v1/chat/sessions/{id}/role-claims` |

## Mid-chat model swap

Run cards in Chat show an **Agents** strip with per-role model badges. Click a badge to swap; click **ⓘ** for battery details and Ollama pull CTA. Swaps emit `model.binding.overridden` on the run event stream and appear in theater as `model_swap` lines. IDE parity: MCP tool `nimbusware_swap_role_model`.


## Related

- [Install profiles](install-profiles.md)
- Per-role bindings (Track A): Settings **Agent & Models** → Model Hub for missing connections
