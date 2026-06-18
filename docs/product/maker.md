# Maker app

Web entry: `GET /v1/maker/app/` ([`packages/nimbusware_maker_web`](../../packages/nimbusware_maker_web/static/)).

Launch: `poetry run nimbusware-maker` or `poetry run nimbusware-run` (pywebview). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`). On Enterprise, set `NIMBUSWARE_API_KEY` (user-scoped key).

## Tabs

| Tab | Purpose |
|-----|---------|
| **Home** | Readiness, hardware strip, intents, factory catalog demos |
| **Chat** (default) | Classify intent → work type → start run or campaign |
| **Build** | Redirects to Chat; legacy API flow still available |
| **Progress** | SSE theater, maker-progress, findings, operator ribbons |
| **Review** | Research approve/reject, slice approval, factory evidence, audit export |
| **Plan** | Campaign backlog tree, steer actions |
| **Models** | Model Hub — Ollama + API connections |
| **Settings** | Hardware, Ollama, autopilot, hybrid routing presets |

PWA manifest + offline service worker; Web Push when VAPID configured. Deep links: `?run_id=`.

## Chat

- Rules-first intent classifier with optional LLM (`NIMBUSWARE_INTENT_CLASSIFIER_MODEL`)
- **Work types:** `quick`, `patch`, `slice`, `campaign`, `factory` → workflow profiles; frozen on `run.created`
- Live **run theater** with severity and evidence toggles in run cards
- Session sidebar, fork/branch tree, trust/autopilot ribbons
- Escalation: patch fail → slice widen; repeated gate fail → campaign promotion
- APIs: `POST /v1/chat/sessions`, `POST /v1/chat/classify`, `POST /v1/chat/sessions/{id}/start`, fork/graph/switch-mode
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

Default workflow profile: `nimbusware_production` (live writers). Slice auto-advance on by default (`NIMBUSWARE_SLICE_AUTO_ADVANCE` unset or `1`).
