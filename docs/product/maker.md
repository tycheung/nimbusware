# Maker app

Web entry: `GET /v1/maker/app/` ([`packages/nimbusware_maker_web`](../../packages/nimbusware_maker_web/static/)).

Launch: `poetry run nimbusware-maker` or `poetry run nimbusware-run` (pywebview). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`). On Enterprise, set `NIMBUSWARE_API_KEY` (user-scoped key).

## Tabs

| Tab | Purpose |
|-----|---------|
| **Home** | Readiness, hardware strip, intents, full-stack demo prompts |
| **Chat** (default) | Classify intent → scope discovery (full-stack) → start run or campaign |
| **Build** | Redirects to Chat; campaign mode uses `campaign_fullstack` with recommend-for-me |
| **Progress** | SSE theater, maker-progress (incl. enforcement chip), findings, operator ribbons |
| **Review** | Research approve/reject, slice approval, factory evidence, audit export |
| **Plan** | Campaign backlog tree, steer actions |
| **Models** | Model Hub — Ollama + API connections |
| **Settings** | Hardware, Ollama, autopilot, enforcement depth defaults, hybrid routing presets |

PWA manifest + offline service worker; Web Push when VAPID configured. Deep links: `?run_id=`.

## Chat

- Rules-first intent classifier with optional LLM (`NIMBUSWARE_INTENT_CLASSIFIER_MODEL`)
- **Work types:** `quick`, `patch`, `slice`, `campaign`, `factory` → workflow profiles; frozen on `run.created`
- **Full-stack campaigns:** greenfield product prompts route to `campaign_fullstack`; scope discovery runs in Chat before Start (`POST /v1/chat/scope/discover`, `/scope/gather`, `/scope/recommend`)
- **Start gate:** full-stack campaigns require completed discovery or **Recommend for me** (backend-only phrasing skips to `campaign_micro_slice`)
- Live **run theater** with severity and evidence toggles in run cards (trust + enforcement chips)
- Session sidebar, fork/branch tree; active-run **trust/autopilot** and **enforcement depth** ribbons (shared `autopilot-ribbon.js` / `enforcement-ribbon.js`)
- Escalation: patch fail → slice widen; repeated gate fail → campaign promotion
- APIs: `POST /v1/chat/sessions`, `POST /v1/chat/classify`, `POST /v1/chat/sessions/{id}/start`, `POST /v1/chat/scope/discover`, fork/graph/switch-mode
- MCP tools: [ide-bridge.md](../ide-bridge.md); ADRs [020](../adr/020-unified-chat-work-type-routing.md), [021](../adr/021-conversation-dag-branching.md)

## Progress & Review

- Theater SSE: `GET /v1/runs/{id}/theater`, `/theater/stream`, `/theater/export`
- Maker progress: `GET /v1/runs/{id}/maker-progress`, SSE with `?simple=true`
- Memory influence: `GET /v1/runs/{id}/memory-influence`
- Research: `GET /v1/runs/{id}/research`, POST approve/reject
- Stitch: `GET /v1/runs/{id}/stitch-summary`
- Slice approval: `GET /v1/runs/{id}/maker/pending`, plan approve, slice prepare/apply/skip
- Factory evidence scorecard + zip: `GET /v1/runs/{id}/factory-evidence`
- Compliance bundle: `GET /v1/runs/{id}/audit-export`
- Launch check: `POST /v1/runs/{id}/maker/launch-eval` — see [reference/launch-eval.md](../reference/launch-eval.md)

## Operator controls

- **Trust/autopilot slider** — `GET/PUT /v1/runs/{id}/autopilot`; presets in `configs/autopilot/presets.yaml`
- **Enforcement depth slider** — `GET/PUT /v1/runs/{id}/enforcement`; presets in `configs/enforcement/presets.yaml`; saved profiles in `configs/enforcement/user_profiles.yaml`; level 10 = workspace CI parity + terminal `enforcement.gate` (ADR [026](../adr/026-enforcement-depth-slider.md)). Progress tab shows `enforcement_status` chip; Build/Campaign start honor Settings default profile.
- **Enterprise enforcement policy** — Admin Fleet page + `GET/PUT /v1/enterprise/tenants/{ref}/enforcement-policy` clamps tenant min/max depth
- **Interjection queue** — `[patch]`, `[steer]`, `[skip]`, `[build]` prefixes; ADRs [013](../adr/013-operator-interjection.md)–[015](../adr/015-custom-autopilot-profiles.md)
- **Compaction** — revert via `POST /v1/runs/{id}/compactions/{compaction_id}/revert`
- **Dev env ribbon** — start/stop/regression when persistent dev env enabled

## v1.2 features

- **Model Hub** — [model-hub.md](../model-hub.md)
- **Per-role model routing** — Settings Agent & Models grid; ADR [022](../adr/022-per-role-model-routing.md)
- **Hybrid routing** — [hybrid-routing-migration.md](../hybrid-routing-migration.md)
- **Collaborative chat** — `NIMBUSWARE_COLLAB_ENABLED=1`; [collaborative-chat.md](../collaborative-chat.md)
- **Compute mesh** — [compute-mesh.md](../compute-mesh.md)
- **Conversation library** — [conversation-library.md](../conversation-library.md)

Default workflow profile: `micro_slice`. Chat projects may override via `default_workflow_profile`. Slice auto-advance on by default (`NIMBUSWARE_SLICE_AUTO_ADVANCE` unset or `1`).
