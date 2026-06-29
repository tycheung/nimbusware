# Maker app

Web entry: `GET /v1/maker/app/` ([`packages/nimbusware_maker_web`](../../packages/nimbusware_maker_web/static/)).

Launch: `poetry run nimbusware-maker` or `poetry run nimbusware-run` (pywebview). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`). On Enterprise, set `NIMBUSWARE_API_KEY` (user-scoped key).

## Tabs

| Tab | Purpose |
|-----|---------|
| **Home** | Readiness, hardware strip, intents, full-stack demo prompts |
| **Chat** (default) | Classify intent → scope discovery (full-stack) → start run or campaign |
| **Build** | Redirects to Chat; campaign mode uses `campaign_fullstack` with recommend-for-me |
| **Progress** | SSE theater (Evidence toggle per line), maker-progress with surface-aware slice headlines, deploy cockpit (validate, approve, apply, smoke, rollback, environment selector), findings panel, operator ribbons |
| **Review** | Research approve/reject, slice approval, deploy cockpit + git/PR panel, factory evidence, audit export |
| **Plan** | Campaign backlog tree with surface badges (API/Web/Infra/Contract), active slice highlight, maintenance countdown, contract gate card, steer actions |
| **Models** | Model Hub — Ollama + API connections |
| **Settings** | Hardware, Ollama, autopilot, enforcement depth, hybrid routing, deploy credential vault sync, solo discipline hat, **My agent overlays** editor, collab toggle |

PWA manifest + offline service worker; Web Push when VAPID configured. Deep links: `?run_id=`.

## Chat

- Rules-first intent classifier with optional LLM (`NIMBUSWARE_INTENT_CLASSIFIER_MODEL`)
- **Work types:** `quick`, `patch`, `slice`, `campaign`, `factory` → workflow profiles; frozen on `run.created`
- **Full-stack campaigns:** greenfield product prompts route to `campaign_fullstack`; scope discovery runs in Chat before Start (`POST /v1/chat/scope/discover`, `/scope/gather`, `/scope/recommend`, `/scope/confirm`)
- **Scope discovery:** chips + **Explain** hints per question; **Recommend for me**; plain-language manifest approval card; `@web` / `@api` surface steers
- **Stack manifest:** confirmed manifest freezes surfaces (`api`, `web`) and stacks from `configs/stacks/`; per-stack diff budgets; Plan tab shows surface badges and `slice.contract` gate status
- **Manifest approval:** Chat shows a plain-language “You are approving: web UI + REST API…” card with **Approve manifest** before campaign start
- **Safe Coding campaigns:** archetype `safe_coding` routes greenfield builds to `safe_coding_campaign_fullstack` (campaign driver + approval gates + OWASP web critic pack)
- **Solo discipline hat:** Settings → **Solo discipline hat** routes `@` mentions (and the active hat) into `solo_discipline_routes` on requirements when working alone
- **Collab disciplines:** join discipline picker, roster badges, `@` routing to interjection queue, routed-feedback thread lines; expertise bullets via `GET/PUT /v1/users/me/participant-context`; per-discipline agent overlays via Settings **My agent overlays** or `GET/PUT /v1/users/me/agent-overlays/{discipline}` (versioned; `collab.agent_overlay.updated` audit in `.nimbusware/platform/collab_audit.jsonl`) merged into slice prompts when roles are claimed; MCP `nimbusware_set_discipline` / `nimbusware_update_agent_overlay` and VS Code extension scope/`@` commands for IDE parity ([ide-bridge.md](../ide-bridge.md))
- **Collab composer:** `@frontend`, `@backend`, `@qa`, `@architect`, `@pm`, `@devops` mention autocomplete in Chat; invite modal loads templates from `configs/collab/invite_templates.yaml` via `GET /v1/platform/invite-templates`
- **Start gate:** full-stack campaigns require completed discovery, confirmed manifest, or **Recommend for me** (backend-only phrasing skips to `campaign_micro_slice`)
- Live **run theater** with severity and evidence toggles in run cards (trust + enforcement chips)
- **Open preview** link on active run cards when dev environment session is live; **Live API / Live web** links when deploy timeline includes URLs (`GET /runs/{id}/dev-env/status`, run timeline metadata)
- Session sidebar, fork/branch tree; active-run **trust/autopilot** and **enforcement depth** ribbons (shared `autopilot-ribbon.js` / `enforcement-ribbon.js`)
- Escalation: patch fail → slice widen; repeated gate fail → campaign promotion
- APIs: `POST /v1/chat/sessions`, `POST /v1/chat/classify`, `POST /v1/chat/sessions/{id}/start`, `POST /v1/chat/scope/discover`, fork/graph/switch-mode
- MCP tools: [ide-bridge.md](../ide-bridge.md); ADRs [020](../adr/020-unified-chat-work-type-routing.md), [021](../adr/021-conversation-dag-branching.md)

## Progress & Review

- Theater SSE: `GET /v1/runs/{id}/theater`, `/theater/stream`, `/theater/export` — structured lines with severity borders and **Evidence** toggles (same as Chat run cards)
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
- **Interjection queue** — `[patch]`, `[steer]`, `[steer:web]` / `[steer:api]`, `@web` / `@api` surface steers, `[skip]`, `[build]` prefixes with chip picker in Progress and Chat; ADRs [013](../adr/013-operator-interjection.md)–[015](../adr/015-custom-autopilot-profiles.md)
- **Deploy cockpit** — Progress and Review show CI/plan/approval from run timeline; refresh polls GitHub Actions via `POST /v1/platform/deploy/ci-poll` when Settings lists a `github_repo`; **Run Terraform validate** posts stages; **Approve deploy** records `deploy.approved`; **Apply deploy** runs gated `terraform apply` (snapshots state before apply); **Run smoke test** hits live API/web URLs; **Rollback deploy** runs destroy or previous-state restore; environment selector (`dev` / `staging` / `prod`) passes `TF_VAR_environment` to Terraform; Settings syncs deploy labels with `GET/PUT /v1/platform/deploy/credentials`. Enterprise tenants enforce allowed deploy targets from fleet deploy policy. Campaigns with `deploy` in the frozen manifest require a successful `deploy.smoke` stage before **completion_eval** may PASS ([deploy.md](deploy.md)).
- **Findings workspace** — blocking findings by default; toggle **Show all severities** for full gate output; interject/widen actions on blockers
- **Completion cockpit** — plain-language terminal banner when campaigns finish (Safe Coding archetype uses softer “passed automated checks” copy); auto **launch check** on terminal runs; per-surface launch summary chips
- **Review git panel** — branch, PR URL, PR status, and deploy CI timeline status from the same run
- **Enterprise Home** — `GET /v1/platform/fleet-governance` surfaces mandatory discovery fields, deploy approval chain, default surfaces, allowed deploy targets, and enforcement depth clamps; `GET /v1/enterprise/compliance/summary` loads gate pass rate and fleet policy counts in the compliance widget
- **Review commit policy** — enterprise Review git panel shows conventional-commit and ticket-id chips when fleet commit policy applies (`GET /v1/enterprise/tenants/{ref}/commit-policy`)
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
