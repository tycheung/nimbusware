# All LLMs + collaborative group chat + distributed resource sharing (v1.2 program)

> **Status:** **Shipped MVP** (Jun 2026). Extends shipped v1.1 hybrid routing (fo1310–fo1313) and congruent Chat (§20.28 / fo1180–fo1259).
> **References:** normative [`nimbusware-orchestrator-local-plan.md`](nimbusware-orchestrator-local-plan.md) (§19.5, §20.8, §20.28, §20.29), engineering [`PLAN_GAP.md`](PLAN_GAP.md), market ledger [`v1.1features.md`](v1.1features.md), boundary doc [`docs/integrations-external-chat.md`](docs/integrations-external-chat.md).  
> **Supersedes (partially):** stage-level `cloud_runtime` + `stage_providers` in [`configs/model-routing.yaml`](configs/model-routing.yaml) — migrated in fo1471, not deleted.

---

## Executive summary

| Dimension | v1.1 (shipped) | v1.2 target (this program) |
|-----------|----------------|----------------------------|
| **Routing granularity** | Stage-level presets (`plan`, `slice.critique`) | **Role-level** + stage fallback + user profile defaults |
| **Providers** | Single OpenAI-compatible cloud block | **Local (Ollama) + N cloud providers** per binding |
| **Preflight** | Ollama required; cloud probe optional | **Provider-aware readiness** — Ollama not mandatory when cloud bindings cover active roles |
| **Operator UX** | Settings hybrid preset dropdown | **Agent & Models** panel — map each role to a model; swap mid-chat |
| **Chat congruence** | Theater shows `actor_display` | **Per-actor model badge** + live swap; **human peanut gallery** with session roles |
| **Collaboration** | Single operator per browser; localhost open | **Invite link (Individual)** or **org directory (Enterprise)**; read / write / admin participant roles; **folders / groups / tags** for conversation library + bulk ACL |
| **Default posture** | Local-first, cloud opt-in | **Local-first defaults per role**, cloud per-role opt-in — not local-only nor cloud-only |
| **First install** | `--install-profile` recommended (default) or barebones | Model Hub API connections (C2) |
| **Model / API UX** | Models tab = Ollama rank + pull only; API keys in `.env` only | **Model Hub** tab — local models + **API connections** (keys in UI vault); **battery detail popover** + one-click Ollama pull |
| **Compute** | Single machine; `asyncio.gather` + optional Enterprise Redis fleet worker | **Host-coordinated mesh** — parallel stages on **claimer’s machine** (`execute_on: self` only); host transfer with timed consent |
| **Workload assignment** | Host runs all agents | **Manual claim**, **auto share**, or **auto optimize**; unlimited claims with compute headroom warnings |
| **Secrets** | `.env` on host | **API keys never leave each user’s machine** — batteries are local vault refs; host sees metadata catalog only with delegate permission |

**Verdict:** Four coupled tracks in one release train:

1. **Track C (fo1590–fo1620)** — universal installer + **Model Hub** — **first user touchpoint**.
2. **Track A (fo1400–fo1499)** — per-role model routing + mid-chat swap.
3. **Track B (fo1500–fo1589)** — collaborative **group chat** + **conversation library** (folders, groups, tags, bulk ACL).
4. **Track D (fo1700–fo1799)** — **resource sharing**: remote execution always on claimer’s machine; host transfer; admin **Accessible compute** panel; batteries per-user (no key exchange).

---

# Track A — Per-role model routing & mid-chat swap

## Shipped baseline (Jun 2026)

### Legacy vs current

| Capability | Location | Status |
|------------|----------|--------|
| Ollama primary runtime | `configs/model-routing.yaml` → `runtime` | Legacy global default; superseded by per-role bindings |
| Hybrid presets | `configs/routing_presets.yaml`, `hybrid_routing.py` | Shim for unmapped stages; presets migrated (A7) |
| Model Manager | Maker **Model Hub** (`#/models`) | Per-role fit/rank via `ModelBindingResolver` + profile defaults |
| Role registry | `configs/roles.yaml`, Postgres `nimbusware_roles_registry` | Agent identity; model binding via `configs/model_bindings/` |
| Custom agents | `configs/custom_agents/registry.yaml` | System prompt + optional `bound_role_id`; inherits role binding |
| Chat theater | `run_theater.py` | Agent + model badge; mid-chat swap events (A5) |
| Preflight | `binding_preflight.py`, readiness API | Per-role `roles_covered` / `providers_reachable` (A3) |
| **Universal installer** | `scripts/install_nimbusware.py` | **`--install-profile`** recommended (default) / barebones (C1) |
| **Model Hub** | `#/models`, `models.js` | Ollama install/pull + **API connections** vault (C2/C3) |

### Resolver wiring (fo1422 — closed)

- All orchestrator/maker LLM entry points route through `ModelBindingResolver` via `ollama_chat_json_via_plan_patch` or direct resolver calls.
- Stage → role mapping in `binding_preflight.agent_role_for_stage` covers `slice.*`, `plan`, and `*.critique` stages.
- Audit matrix: `docs/audits/llm-call-sites.md`.

## North star (Track A)

**Flexible inference routing:** for every Nimbusware **agent role** (planner, backend_writer, security_critic, …) and every **custom agent**, the operator defines:

1. A **default binding** on their **user profile** (persisted in Postgres).
2. An optional **run-level override** frozen on `run.created` (like `policy_snapshot`).
3. An optional **mid-run / mid-chat swap** that emits an auditable event and applies to **subsequent** LLM calls for that role only.

**Neither local-only nor cloud-only:** a run may use Ollama for writers, OpenAI for planner, Anthropic for security critic, and Grok for debugger — concurrently in the same Chat thread.

**Preflight honesty:** readiness reports which roles lack a reachable provider; **does not block** start when Ollama is down if all **active workflow roles** have healthy cloud bindings.

## Architecture — model routing

```text
┌─────────────────────────────────────────────────────────────────┐
│  Maker Chat / Settings / Admin                                   │
│  • Agent & Models panel (profile defaults)                       │
│  • Per run-card: agent role → model badge + "Swap model"         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ GET/PUT profile, POST swap
┌───────────────────────────▼─────────────────────────────────────┐
│  API — model_bindings (nimbusware_config_document)               │
│  namespace: model_bindings  keys: user_defaults | tenant_policy  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ materialize
┌───────────────────────────▼─────────────────────────────────────┐
│  ModelBindingResolver (orchestrator)                             │
│  resolve(agent_role, *, stage, run_id, session_id) → Binding    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   OllamaProvider    OpenAICompatProvider   (future adapters)
```

### Provider binding (normative schema)

```yaml
binding:
  provider_kind: local | cloud
  provider_id: ollama | openai | anthropic | openrouter | custom
  model_id: "qwen2.5-coder:14b"
  base_url: null
  api_key_ref: OPENAI_API_KEY
  params:
    temperature: 0.2
    max_output_tokens: 8192
  json_mode: true
  cost_hint_per_1k_tokens_usd: 0.003
```

### Resolution precedence

| Priority | Source | Scope |
|----------|--------|-------|
| 1 | `workload.role_claimed` → claimer’s binding snapshot | Single agent role; execution pinned to claimer’s node when compute opted-in |
| 2 | `model.binding.overridden` event | Single agent role, from swap forward |
| 3 | `run.created` → `model_bindings_snapshot` | Whole run |
| 4 | Chat session `role_binding_overrides` | Session (mid-chat swap) |
| 5 | User profile `model_bindings/user_defaults` | Operator preference |
| 6 | Workflow profile `model_bindings` block | Profile default |
| 7 | Platform `model-routing.models.primary` | Global fallback |

## Track A — Epic program (fo1400–fo1499)

### Phase A0 — Contract & ADR (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1400** | Normative §20.30 + ADR | `docs/adr/022-per-role-model-routing.md` | Precedence table, event types, non-goals signed off |
| **fo1401** | Gap closure audit | Matrix: every `*_chat_json` / `ollama_chat_json` call site → resolver | No orphan direct Ollama calls after A2 |

### Phase A1 — Provider layer (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1410** | `LlmProvider` protocol | `nimbusware_orchestrator/llm/providers/` | Unit tests per provider |
| **fo1411** | Ollama provider | Wrap existing `ollama_chat_json` | Parity with preflight JSON mode |
| **fo1412** | OpenAI-compatible provider | Generalize `cloud_chat_json` | OpenAI + OpenRouter smoke tests |
| **fo1413** | Provider registry | `configs/model_providers.yaml` + Postgres doc | List providers without code change |
| **fo1414** | Credentials policy | `api_key_ref` → env **or** UI vault ref (`connection_id`); never log/plaintext in events | No secrets in chat turns or audit export |

**Depends on:** fo1400. **Soft dependency:** fo1593 (UI connection store) for vault refs.

### Phase A2 — Binding config & resolver (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1420** | Binding schema + seed | `configs/model_bindings/defaults.yaml` | Materializer loads bindings |
| **fo1421** | `ModelBindingResolver` | `resolve_llm(agent_role, *, stage, run_id, session_id)` | Unit matrix for precedence |
| **fo1422** | Replace dispatch fan-out | All LLM call sites → resolver | fo1401 matrix **green** |
| **fo1423** | Run snapshot | `model_bindings_snapshot` on `run.created` | Replay reproduces bindings |
| **fo1424** | Role telemetry extension | `provider_id`, `model_id`, `binding_source` on inference events | Progress cost summary |

### Phase A3 — Relaxed preflight (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1430** | Provider-aware preflight | `roles_covered`, `providers_reachable` | Ollama skip when all roles cloud-bound |
| **fo1431** | Readiness API | `roles_without_provider`, per-provider probe | Home wizard no hard-fail on missing Ollama |
| **fo1432** | Workflow-scoped coverage | Active roles from workflow + work_type | Patch lane scoped correctly |
| **fo1433** | Degraded mode labels | “Cloud-only” / “Hybrid” banners | Theater System line on run start |

### Phase A4 — Settings UI (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1440** | Profile API | `GET/PUT /v1/platform/model-bindings/defaults` | Postgres persist |
| **fo1441** | Role catalog API | `GET /v1/platform/model-bindings/roles` | Includes custom agents |
| **fo1442** | **Settings → Agent & Models** tab | Role × Provider × Model grid | Playwright green |
| **fo1443** | Provider picker in Settings | Bindings grid picks from Model Hub connections | Removed duplicate key entry |
| **fo1444** | Settings ↔ Model Hub link | fo1598 cross-links; Agent & Models does not duplicate API key forms | Single place for secrets |
| **fo1445** | Import/export | `model_bindings/*` in config export | Gitops diff |

#### fo1442 UI — Agent & Models (Settings)

**Route:** `#/settings` → **Agent & Models** (`data-testid="maker-settings-agent-models"`).

```text
┌──────────────────────────────────────────────────────────────────┐
│ Agent & Models                                    [Test all] [Save]│
├──────────────────────────────────────────────────────────────────┤
│ Global fallback:  [ qwen2.5-coder:14b ▼ ] Ollama                  │
│ Active providers: [Ollama ✓] [OpenAI ✓] [Anthropic ○] [+ Add]    │
├──────────────────────────────────────────────────────────────────┤
│ Agent role        │ Provider    │ Model              │ Status │ ⋮  │
│ Planner           │ OpenAI      │ gpt-4o             │   ✓    │ … │
│ Backend Writer    │ Ollama      │ qwen2.5-coder:14b  │   ✓    │ … │
│ Security Critic   │ Anthropic   │ claude-sonnet-4    │   ○    │ … │
└──────────────────────────────────────────────────────────────────┘
```

**Link to Model Hub:** when a provider has no saved connection, show “Configure in Models → API connections” → `#/models#api-connections`.

**Depends on:** fo1420, fo1430, fo1594–fo1596 (Model Hub).

### Phase A5 — Mid-chat model swap (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1450** | Swap API | `POST /v1/runs/{id}/model-bindings/swap` | Emits `model.binding.overridden` |
| **fo1451** | Session-scoped swap | `POST /v1/chat/sessions/{id}/model-bindings/swap` | Chat-first path |
| **fo1452** | Chat UI — swap control | Run card **Agents** strip with model badges | Swap mid-thread |
| **fo1453** | Theater rendering | `model_swap` line kind + `model_display` | System notice in thread |
| **fo1454** | MCP tool | `nimbusware_swap_role_model` | IDE parity |
| **fo1455** | Stage safety | Swap applies after current stage or confirm | No half-written JSON |
| **fo1456** | **Role claim API** | `POST /v1/chat/sessions/{id}/role-claims` body `{ run_id, agent_role, binding }` — always **`execute_on: self`** | Emits `workload.role_claimed`; write+ only |
| **fo1457** | Claimer binding scope | Worker resolves LLM from **claimer’s** Model Hub only; no cross-user key refs | fo1421 extension |
| **fo1458** | Release / reassign | `DELETE …/role-claims/{agent_role}`; admin reassign → finish-or-restart handoff (fo1782) | Emits `workload.role_released` |
| **fo1459** | **Battery detail popover** | Click model badge in theater / Agents strip | Agent role, model id, provider label, executor `@username`, node label |
| **fo1460** | **Model pull CTA** | If viewer lacks local Ollama model → download icon → `#/models#local` + `POST /platform/ollama/pull` | fo1611 queue |
| **fo1461** | Cloud battery display | Show provider + model hint only; link to viewer’s **API connections** tab — never show/export keys | fo1612 |
| **fo1462** | Theater `battery_detail` line | Optional expand on agent lines | Same fields as popover |

#### fo1452 UI — Agent model strip (Chat run card)

**Surface:** `#/chat?run_id=` → run card → below trust ribbon.

```text
Agents:  [Planner · gpt-4o ⓘ] [Writer · qwen ⓘ · Claim] [Sec.Critic · claude ⓘ]
         [Writer · alex@node · qwen2.5-coder:14b]  [Release] [Terminate & restart on me]
```

- **session_write+** may **Claim** any number of parallel roles; UI warns when claimer’s **free compute headroom** is lower than other online participants with spare capacity (fo1785).
- **Battery picker** lists only **your** local Ollama models + **your** saved API connections (ChatGPT subscription, Claude API, etc.) — keys stay on your machine.
- **ⓘ popover (fo1459):** agent name · model · provider · `@executor` · node; **[↓ Pull model]** if you lack that Ollama tag locally.
- **Handoff (fo1782):** claimed role finishes **current in-flight stage** on prior executor, then next unit runs on claimer’s node; claimer may **Terminate & restart on me** to skip wait.
- **session_read** sees popover (read-only) + claimer names; no Claim/Release.
- **session_admin** may release/reassign claims; with guest **delegate permission** may configure bindings in guest environment (fo1786).

#### fo1459 UI — Battery detail popover

**Trigger:** click **ⓘ** on model badge in Agents strip or theater agent line.

```text
┌─ Backend Writer ──────────────────────────────────────┐
│ Battery:  qwen2.5-coder:14b  (Ollama local)           │
│ Executor: @alex · alex-mac · GPU · 6/8 slots free     │
│ Host merge: ★ host-machine (canonical)                 │
│ [ ↓ Pull qwen2.5-coder:14b ]  ← if viewer lacks model │
│ [ Open Model Hub → Local ]                              │
└────────────────────────────────────────────────────────┘
```

Cloud battery variant: `Claude · claude-sonnet-4 · @sam` + link to **your** API connections if you want the same provider — never copies sam’s key.

### Phase A6–A8 — Enterprise policy, migration, quality

| Phase | Epics | Summary |
|-------|-------|---------|
| **A6** | fo1460–fo1462 | Admin model policy, egress, audit export |
| **A7** | fo1470–fo1473 | Hybrid preset migration, docs, settings catalog |
| **A8** | fo1480–fo1483 | E2E, OpenAPI, benchmarks, cost summary |

---

# Track C — Universal installer & Model Hub

## Installer / setup audit (Jun 2026 — current codebase)

Single entrypoint: **`scripts/install_nimbusware.py`** (wrapper; implementation in `scripts/install/install_nimbusware.py`). Shell wrappers: `install-nimbusware.ps1`, `install-nimbusware.sh`. Consumer hints: **`nimbusware-bootstrap`** wheel, `--consumer-plan`, `--print-one-command`.

| Component | Status | Issue / drift |
|-----------|--------|----------------|
| **Poetry deps + slice LSP** | ✅ Current | Sets `NIMBUSWARE_SLICE_LSP_ENABLED=1`; pyright via `poetry install` |
| **Postgres menu** | ✅ Current | Interactive `postgres_setup_menu.py`; `--non-interactive` defaults Docker or skip |
| **Ollama step** | ✅ **Profile-driven** | `recommended` (default): bootstrap + model pull; `barebones` / `--skip-ollama`: skip |
| **`enable_nimbusware_llm_in_env`** | ✅ | Only when Ollama bootstrap succeeds — barebones skips |
| **Default profile** | ✅ C1 | **`recommended`** default; **`barebones`** via `--install-profile barebones` |
| **Models tab (`#/models`)** | ✅ C3 | Model Hub local + API connections, Ollama install, pull/list |
| **Home readiness** | ✅ C3 | Deep links to Model Hub; inference mode label (A3) |
| **first-install-timing.md** | ✅ C0/C1 | Recommended vs barebones rows documented |
| **Bootstrap `--run`** | ✅ C1 | Barebones uses `--install-profile barebones` |
| **Tests** | ✅ C1 | `test_install_smoke.py`, `test_install_profile.py`, happy-path lines |

**Normative fix:** One **`install_nimbusware.py`** script; **install profile** + **edition** select defaults only (not separate installers). **Recommended** is the default (Ollama + qwen + llama pre-pull); **Barebones** is opt-in for CI/cloud-only/minimal VMs. Extra LLM/API setup always available in **Model Hub**.

## Install profiles & edition matrix

**Two axes, one installer:**

| Axis | Values | Role |
|------|--------|------|
| **`--install-profile`** | `recommended` (default) \| `barebones` | How much LLM/local stack to set up during install |
| **`--edition`** | `individual` (default) \| `enterprise` | Product edition — IAM, fleet, Redis group, etc. |

Profiles **compose** with edition: `individual + recommended` and `enterprise + recommended` share the same Ollama/model steps; enterprise adds its existing extras (Redis Poetry group, enterprise `.env`, optional stricter Postgres default).

### Profile 1 — Recommended (default)

**Purpose:** “Works out of the box” for local LLM — default first-run path; matches historical v1 onboarding expectations (fo1300 TTV).

| Step | Recommended behavior |
|------|---------------------|
| Poetry deps + slice LSP + Postgres menu | ✅ (same baseline as barebones) |
| Ollama | Install/start via platform default (winget / brew / script / GUI download) |
| Model pre-pull | **`qwen2.5-coder:14b`** + **`llama3.1:8b`** from [`configs/model-routing.yaml`](configs/model-routing.yaml) (primary + first fallback) |
| `NIMBUSWARE_USE_LLM` | Set **`1`** in `.env` when Ollama + at least primary model present |
| Preflight hint | Print `poetry run nimbusware-preflight` on success |
| Apply routing | Primary = `llama3.1:8b`; fallback = `qwen2.5-coder:14b` (already seeded YAML; optional `models/apply-preset` balanced on qwen for writers) |

**Timing budget:** add **~2–8 min** for Ollama install + **~5–15 min** model pulls (network/GPU dependent) — document in `first-install-timing.md` as **Recommended profile** row.

**Failure posture:** if Ollama install or pull fails, installer **warns and continues** (falls back to barebones-equivalent LLM posture); Models tab shows retry CTAs.

### Profile 2 — Barebones (opt-in)

**Purpose:** Fastest path to a working control plane — API, Maker, Chat, stub/quick runs — **without** local LLM or large downloads. Use **`--install-profile barebones`** or **`--skip-ollama`**.

| Step | Barebones behavior |
|------|-------------------|
| Poetry deps | ✅ Always |
| Slice LSP (`NIMBUSWARE_SLICE_LSP_ENABLED=1`) | ✅ Always |
| Postgres | Interactive menu (Docker / native / skip) — unchanged |
| Ollama | **Skipped** (`--ollama-choice skip` implied) |
| Model pull | **None** |
| `NIMBUSWARE_USE_LLM` | **Not set** (stub + `--quick` path) |
| Config seed | Only if `--seed-config` or enterprise recommended bundle |

**Happy path:** `poetry run nimbusware-run --quick` → Chat → patch on fixture (**&lt; 5 min** after Poetry).

**LLM later:** Model Hub → install Ollama → pull models → API connections → enable `NIMBUSWARE_USE_LLM=1`.

### Edition defaults (same script, different flag bundles)

| Profile | Individual (`--edition individual`) | Enterprise (`--edition enterprise`) |
|---------|-------------------------------------|-------------------------------------|
| **barebones** | Postgres: menu (Docker default in `--non-interactive` if available). Redis group: **off**. | Postgres: **prefer Docker** in `--non-interactive` (fail loud if skip without URL). Redis group: **on** (existing auto `--with-redis`). IAM bootstrap hint in next-steps. |
| **recommended** | Barebones + Ollama + dual model pull + `USE_LLM=1`. Postgres: same as barebones individual. | Barebones enterprise + Ollama + dual model pull + `USE_LLM=1`. **`--seed-config`** after schema. Redis + fleet compose hint in next-steps. |

**Not separate installers:** wrappers invoke the same script:

```bash
# Individual recommended (default — Ollama + qwen + llama)
python scripts/install_nimbusware.py

# Individual barebones (minimal / CI / cloud-only later)
python scripts/install_nimbusware.py --install-profile barebones

# Enterprise recommended (default for edition — fleet + local LLM)
python scripts/install_nimbusware.py --edition enterprise

# Enterprise barebones (control plane only, no local LLM)
python scripts/install_nimbusware.py --edition enterprise --install-profile barebones
```

**Consumer / curl paths** (update fo1595):

```bash
# Recommended consumer (default — demo machine with GPU)
curl -fsSL …/install_nimbusware.py | python - --clone … --non-interactive \
  --install-profile recommended

# Barebones consumer (fast VM / CI)
curl -fsSL …/install_nimbusware.py | python - --clone … --non-interactive \
  --skip-postgres --install-profile barebones
```

### Interactive installer UX (normative)

After Poetry deps (and before or after Postgres menu — **after Postgres** preferred):

```text
================================================================================
How much do you want to set up now?
================================================================================

  [1] Recommended (default)
      Installs Ollama (if needed) and downloads qwen2.5-coder:14b + llama3.1:8b.
      Enables local LLM runs (NIMBUSWARE_USE_LLM=1). Best for: first-time local dev.

  [2] Barebones
      API + Maker + Chat. No Ollama download. Add models later in Models tab.
      Best for: cloud-only APIs, CI, quick stub runs (nimbusware-run --quick).

  Enter 1 or 2 [default: 1]:
```

If `[1]` and Ollama unreachable → sub-menu from `ollama_setup.build_ollama_setup_options()` (winget / brew / download / skip).

Edition prompt remains **`--edition`** CLI flag or separate first question when not passed:

```text
  Edition: [1] Individual (default)  [2] Enterprise
```

### CLI surface (fo1597 — additive flags)

| Flag | Default | Effect |
|------|---------|--------|
| `--install-profile` | `recommended` | `recommended` \| `barebones` |
| `--edition` | `individual` | Unchanged |
| `--install-profile recommended` | (default) | Implies `--install-ollama` + pull `qwen2.5-coder:14b,llama3.1:8b` unless `--ollama-models` override |
| `--install-profile barebones` | — | Skips Ollama and model pulls |
| `--skip-ollama` | off | Forces barebones LLM behavior even when profile=recommended |
| `--ollama-models` | from YAML | Override recommended pull list |

**Backward compatibility:** bare `--install-ollama` ≡ `--install-profile recommended` (redundant when recommended is default); document in fo1591.

## North star (Track C)

**One universal installer** — same script for Individual and Enterprise (`--edition`) — that completes Poetry, optional Postgres, schema, and config **without requiring Ollama**.

**Model Hub** (`#/models`, nav label **Models** or **Models & APIs**): single operator surface for:

1. **Local models** — Ollama install/start, installed tags/versions, pull, delete, apply preset to routing (extends fo543–fo549).
2. **API connections** — ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), Grok (xAI), OpenRouter, Custom URL; optional Cursor card explains IDE/MCP-only (no LLM API).

Keys stored in **Postgres connection vault** (Individual + Enterprise); `.env` remains supported for install-scope secrets and gitops export.

## Architecture — Model Hub

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Maker #/models  (Model Hub)                                           │
│  ┌─ Local models ─────────────────┐  ┌─ API connections ────────────┐ │
│  │ Ollama status · Install · Pull │  │ OpenAI · Anthropic · Gemini  │ │
│  │ Installed list (name · digest) │  │ Grok · OpenRouter · Custom   │ │
│  │ Preset wizard → model-routing  │  │ [Test] [Save] masked keys    │ │
│  └────────────────────────────────┘  └──────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────────────┐
│  API                                                                     │
│  GET  /platform/ollama/status · POST /platform/ollama/bootstrap          │
│  GET  /platform/provider-connections · PUT/DELETE …/connections/{id}     │
│  POST /platform/provider-connections/{id}/probe                          │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────────────┐
│  Postgres: nimbusware_provider_connection (encrypted secret blob)      │
│  + existing /platform/ollama/* pull jobs                               │
└────────────────────────────────────────────────────────────────────────┘
```

### Provider connection (normative schema)

```yaml
connection:
  connection_id: uuid
  provider_id: openai | anthropic | google | xai | openrouter | custom
  label: "My ChatGPT"
  base_url: null              # required for custom / openrouter override
  default_model_id: gpt-4o    # optional hint for bindings grid
  secret_ref: vault:…         # never returned on GET; GET returns secret_set: true
  last_probe_at: timestamp
  last_probe_ok: bool
```

## Track C — Epic program (fo1590–fo1619)

### Phase C0 — Installer audit & doc sync (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1590** | Setup audit checklist | This section kept in sync with code | All rows ✅ or tracked |
| **fo1591** | Doc refresh | `README.md`, `first-install-timing.md`, `.env.example`, `nimbusware_bootstrap` README/cli | Cloud-only + skip-Ollama paths documented |
| **fo1592** | Install smoke tests | Barebones + recommended profile smoke; consumer-plan documents both | CI green |

### Phase C1 — Install profiles & optional Ollama (1–2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1593** | **`--install-profile`** | `recommended` (default) vs `barebones`; profile resolver in `install_nimbusware.py` | Matrix above implemented |
| **fo1594** | Interactive profile menu | Barebones vs Recommended prompt + edition prompt | Non-interactive: `--install-profile` only |
| **fo1595** | Recommended bundle | Ollama bootstrap + pull **`qwen2.5-coder:14b`** + **`llama3.1:8b`** + `USE_LLM=1` on success | Warn-and-continue on pull fail |
| **fo1596** | Edition × profile defaults | Individual vs Enterprise Postgres/Redis/seed defaults table | Enterprise recommended runs `--seed-config` |
| **fo1597** | Consumer + bootstrap paths | curl / `nimbusware-bootstrap` document both profiles | fo1592 tests for barebones + recommended |
| **fo1598** | `.env` + next-steps | Recommended: preflight hint; barebones: points to Model Hub (no “Ollama required” on failure) | Profile-specific completion text |

**Depends on:** fo1590. **Blocks:** cloud-only onboarding (Track A fo1431).

**Supersedes** prior C1 “default skip only” — **recommended** is default full local stack; **barebones** is explicit opt-in minimal.

### Phase C2 — API connection vault (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1600** | `nimbusware_provider_connection` table | Encrypted at rest; tenant + user scope | Migration in `postgres.sql` |
| **fo1601** | CRUD + probe API | `GET/PUT/DELETE /v1/platform/provider-connections` | OpenAPI + auth (admin token on non-loopback) |
| **fo1602** | Provider presets catalog | API-key providers **and subscription-style** (ChatGPT Plus, Claude Pro, etc.) in `configs/model_providers.yaml` | fo1413 registry aligned |
| **fo1603** | Gemini adapter | Google AI OpenAI-compatible base URL in fo1412 or dedicated probe | Probe green with test key |
| **fo1604** | Export/import | `nimbusware-config export` redacts secrets; imports connection metadata only | Gitops safe |
| **fo1605** | **Subscription connection type** | `connection_kind: api_key \| subscription`; OAuth/device-flow or manual “connected via app” flag; probe differs from API key | User-owned credentials on **their** machine only |

**Depends on:** fo1410–fo1413 (Track A1). Can start fo1600 schema in parallel with A1.

### Phase C3 — Model Hub UI (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1610** | Tab shell refactor | `models.js` → two sections with hash anchors `#local`, `#api-connections` | Nav may read “Models” (subtitle in tab) |
| **fo1611** | **Local models** panel | Ollama reachable badge; **Install Ollama** (calls `POST /platform/ollama/bootstrap` with winget/brew/download choice); list `GET /platform/ollama/models` with name + digest/size; pull + delete; retain preset wizard | Playwright: install CTA when down |
| **fo1612** | **API connections** panel | Card per provider; API key input (password field); Test + Save; masked “••••sk-…abc” when set | fo1601 API wired |
| **fo1613** | Cursor card | Static explainer: “Cursor Composer is IDE-only — use MCP bridge” + link `docs/ide-bridge.md` | Not a saveable connection |
| **fo1614** | Home/readiness links | Replace `start_ollama` / `pull_model` toasts → `#/models#local` / `#/models#api-connections` | fo1590 drift closed |
| **fo1615** | Settings cross-link | fo1444: Agent & Models links to Model Hub for missing connections | No duplicate key forms in Settings |
| **fo1616** | Admin parity (optional) | Admin Config → Provider connections read-only audit for Enterprise | Tenant policy fo1460 |
| **fo1618** | Home profile awareness | Readiness shows `install_profile`; barebones → “Set up local LLM” CTA → Model Hub; recommended → preflight status | fo1593 UX closure |

#### fo1610 UI — Model Hub layout

**Route:** `#/models` (`data-testid="maker-model-hub"`).

```text
┌──────────────── Model Hub ────────────────────────────────────────────┐
│ [ Local models ]  [ API connections ]          ← sub-nav or scroll    │
├───────────────────────────────────────────────────────────────────────┤
│ LOCAL MODELS (#local)                                                 │
│ Ollama: ● Running at http://127.0.0.1:11434   [Restart] [Install…]   │
│ Installed:                                                            │
│   qwen2.5-coder:14b   8.9 GB   [Pull update] [Delete]                 │
│   llama3.1:8b         4.7 GB   …                                      │
│ Pull: [ ____________ ] [Pull]                                         │
│ ── Apply preset to routing (existing 3-step wizard) ──                  │
├───────────────────────────────────────────────────────────────────────┤
│ API CONNECTIONS (#api-connections)                                    │
│ ┌ ChatGPT (OpenAI API) ─┐ ┌ ChatGPT (Subscription) ─┐                 │
│ │ Kind: API key          │ │ Kind: Subscription      │                 │
│ │ Key: [••••••••••]      │ │ [ Connect via ChatGPT ] │                 │
│ │ Model hint: gpt-4o     │ │ Model: claude-sonnet-4│                 │
│ │ [Test] [Save]    ✓     │ │ [Test] [Save]    ○    │                 │
│ └────────────────────────┘ └───────────────────────┘                 │
│ ┌ Gemini (Google) ───────┐ ┌ Grok (xAI) ───────────┐                 │
│ …                       │ …                       │                 │
│ ┌ Cursor ───────────────────────────────────────────┐                 │
│ │ IDE bridge only — not an LLM backend. [Open docs] │                 │
│ └───────────────────────────────────────────────────┘                 │
└───────────────────────────────────────────────────────────────────────┘
```

**Install Ollama modal (fo1611):** reuse installer options (winget / download / brew / script / already running) — server-side wrapper around `ollama_setup.bootstrap_ollama(choice=…)`.

### Phase C4 — Quality (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1617** | E2E journeys | Barebones install → Model Hub → first LLM; **recommended** install → preflight green | `tests/e2e/web/` |
| **fo1619** | Operator doc | `docs/model-hub.md` + **`docs/install-profiles.md`** (barebones vs recommended × edition) | Linked from Home + README |
| **fo1620** | Install + API tests | Profile flag matrix; `ollama/bootstrap` respects `ollama_user_policy` | CI install smoke |

---

# Track B — Collaborative group chat (“peanut gallery”)

## Problem statement (gap vs shipped)

### Shipped in v1.2 (extends §20.28)

| Capability | Location | Notes |
|------------|----------|-------|
| Congruent Chat thread | `#/chat`, `chat.js` | Multi-human when `NIMBUSWARE_COLLAB_ENABLED=1` |
| Session persistence | `nimbusware_chat_session`, `nimbusware_chat_turn` | `host_user_id`, `metadata` (folder/tags via B8 library) |
| Local users | `nimbusware_user`, `/v1/auth/*` | Signup/signin + session cookie |
| Participants | `nimbusware_chat_participant`, `/chat/sessions/{id}/participants` | Invite/join flow |
| Turn roles | `CHAT_TURN_ROLES` + `participant` | Peanut gallery commentary |
| Real-time | `GET /chat/sessions/{id}/stream` | Session SSE (turn + participant fan-out) |
| Interjection | Delegated to `session_write+` when session linked | Audit via participant role |
| Host transfer | `POST /chat/sessions/{id}/host-transfer` | Timed consent MVP ([ADR 026](docs/adr/026-host-transfer.md)) |

### Pre-v1.2 limits (resolved or stubbed)

| Gap (historical) | v1.2 status |
|------------------|-------------|
| One human per browser | **Fixed** — collab auth + participants (B1–B4) |
| No per-user accounts (Individual) | **Fixed** — `nimbusware_auth` |
| No session room fan-out | **Fixed** — session SSE + commentary API (B4) |
| No org directory (Enterprise) | **Stub** — `GET /v1/enterprise/users` (B5) |
| Full folder/group ACL library | **Fixed** — B8 folders/groups/grants + library sidebar |

### Reference — pre-v1.2 baseline (§20.28 only)

| Capability | Location | Limit |
|------------|----------|-------|
| Auth (Individual) | `user.py` | Loopback open unless `NIMBUSWARE_COLLAB_ENABLED=1` |
| External webhook | `docs/integrations-external-chat.md` | Headless — not in-product multi-human UI |

### Terminology (avoid confusion with Track A)

| Term | Meaning |
|------|---------|
| **Project** | Long-lived **workspace container** — `nimbusware_project`: name, `workspace_path`, default workflow profile. One repo/workspace; many chat sessions can belong to one project. |
| **Chat session** | One **congruent conversation thread** — `nimbusware_chat_session`: turn DAG, linked `run_id` / `campaign_id`, title. This is what operators “share” when they send an invite. |
| **Host** | The **one user + machine** that is canonical for a session’s API, event merge, and (Individual) Postgres for **that conversation’s rows**. Stored as `host_user_id` — **not the same as “owner.”** |
| **Owner** | Human who **created** the session (`owner_user_id`); historical audit only after host transfer. |
| **Session participant role** | Human **permission** in a shared chat (`session_admin`, `session_write`, `session_read`) — Track B. **Many `session_admin`s allowed** per session. |
| **Agent role** | Orchestrator taxonomy key (`planner`, `backend_writer`, …) — Track A model binding |
| **Peanut gallery** | Invited humans watching agent theater; may comment or steer per their session role |

### Project vs session vs host (normative)

```text
Project "my-app"  (workspace on disk, default workflow)
├── Chat session "Fix auth bug"     ← one invite link / one shared thread
├── Chat session "Refactor billing"
└── Folder "Q2 patches"
    └── Chat session "Slice 12"
```

| Layer | Shipped today | v1.2 adds |
|-------|---------------|-----------|
| **Project** | Workspace + `project_id` on every session | Folders/tags **organize sessions** within a project (B8) |
| **Session** | Turns, fork DAG, optional `run_id` | Participants, host, collab, claims, mesh |
| **Host** | Implicitly the operator’s machine | Explicit `host_user_id`; transferable admin↔admin (D8) |

**`session_admin` ≠ host:** admins **invite, kick, promote**, and set workload mode. Only the **host** machine holds canonical merge for that session (Individual: local Postgres slice + API; Enterprise: tenant Postgres + fleet — see edition matrix). Multiple admins; **one host** at a time.

## North star (Track B)

**Shared group chat room per project session:** the owner runs agents locally (or on Enterprise fleet); invited humans join as **spectators or participants** in the same congruent thread — seeing classifier cards, run cards, live theater, and (if permitted) posting commentary or interjections.

**Individual edition:** host exposes their instance (public URL or LAN); **invite link** lets guests **create a local login** on the host’s machine and join with a assigned session role.

**Enterprise edition:** invites flow through **org user directory** (tenant-scoped); **external email/link invites disabled** unless tenant admin sets `allow_external_collaborators: true`.

**Not Slack:** no channels, DMs, or general messaging product — peanut gallery is **scoped to an existing Chat session + linked run/campaign**, aligned with §20.5 / §20.28 non-goals boundary.

**Conversation sharing (v1.2):** each **session** is still invited **one conversation at a time** (per-session join link or directory pick). Operators organize many sessions with **folders**, **tags**, and **user groups**, then grant access in bulk (whole folder → group, tag → user, etc.) — see Phase B8.

## Session participant roles (normative)

| Permission | `session_admin` | `session_write` | `session_read` |
|------------|:---------------:|:---------------:|:--------------:|
| Watch live theater + thread | ✓ | ✓ | ✓ |
| View run cards, gate status, trust ribbon | ✓ | ✓ | ✓ |
| Post **commentary** turns in thread | ✓ | ✓ | ✗ |
| **Interject** / steer agents (`[steer]`, `[patch]`, queue) | ✓ | ✓ | ✗ |
| Start run / switch work type / fork branch | ✓ | ✓† | ✗ |
| Swap agent models / **claim role battery** (Track A fo1450, fo1456) | ✓ | ✓ | ✗ |
| Set session **workload mode** (manual / auto share / auto optimize) | ✓ | ✗ | ✗ |
| Change trust / autopilot slider | ✓ | ✗‡ | ✗ |
| **Invite** / revoke participants | ✓ | ✗ | ✗ |
| Promote/demote participant roles | ✓ | ✗ | ✗ |
| **Initiate host transfer** (request to become host, or host → another admin) | ✓§ | ✗ | ✗ |
| **Consent to host transfer** (current host only) | ✓★ | ✗ | ✗ |
| **Grant host delegate control** of my compute (**per session**) | ✓ | ✓¶ | ✗ |

§ Any **session_admin** may initiate transfer **to** another participant; **current host** may initiate transfer **to** another admin. Target must be **`session_admin`** or is **auto-promoted to `session_admin` on accept** if they were write/read. **Admin↔admin only** as final host; non-admin targets are promoted first. Declined/expired → requester **keeps** existing participant role (typically admin).  
★ Shown only to `host_user_id` until `consent_expires_at` (default **24h**, tenant-configurable).  
¶ **`allow_host_resource_management` is per session** (fo1786); revocable without releasing claims.
† **session_write** may start runs only if `write_may_start_runs: true` (default **false**).  
‡ **session_write** may interject but not change autopilot presets.

**Workload modes** (session_admin sets; see Cross-track § below):

| Mode | Who runs parallel agents | How models are chosen |
|------|--------------------------|------------------------|
| **host_only** | Host only | Host run snapshot + host swaps |
| **manual_claim** | Claimed roles → claimer node (`execute_on: self`); unclaimed → host | Claimer picks **their** battery per role |
| **auto_share** | Mesh scheduler → opted-in guest nodes | Guest uses **their** batteries when model matches; else slot stays on **host with host settings** |
| **auto_optimize** | Nimbusware routes across all opted-in nodes | Optimizer picks executor + battery per slot; requires **default share compute** + delegate-capable nodes |

**Default:** `host_only` until session_admin enables another mode (fo1535).

**Default invite role:** `session_read` (safest). Owner upgrades to `session_write` in participant panel.

## Architecture — collaborative chat

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Maker Chat  #/chat  (owner + invited humans)                          │
│  • Participant strip (avatars, roles)                                  │
│  • Thread: user | participant | theater | system turns                 │
│  • Composer gated by session_write | session_admin                     │
└────────────────────────────┬───────────────────────────────────────────┘
                             │ WS or SSE session room
┌────────────────────────────▼───────────────────────────────────────────┐
│  API — chat collaboration                                              │
│  POST /chat/sessions/{id}/invites   GET /chat/join/{token}             │
│  GET  /chat/sessions/{id}/participants                                   │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────────────────┐
│  Postgres                                                                │
│  nimbusware_chat_session (+ owner_user_id, visibility, collab_enabled)   │
│  nimbusware_chat_session_participant                                     │
│  nimbusware_chat_invite                                                  │
│  nimbusware_user (+ credentials Individual | IAM link Enterprise)        │
└──────────────────────────────────────────────────────────────────────────┘
```

### Edition matrix

| Concern | Individual | Enterprise |
|---------|------------|------------|
| **User accounts** | `nimbusware_user` local username/password on host instance | IAM-linked users + OIDC display names |
| **Canonical state** | **Host machine** Postgres (recommended install includes Postgres + preflight) + event store for session | **Centralized tenant Postgres** + fleet workers — shared background compute; collab is **IAM role management** on same fleet |
| **Session “live” hosting** | Session actively hosted on **host’s API**; guests join via link when host is up | Session always backed by **tenant API**; no single laptop must stay online |
| **Mesh / guest GPUs** | Guest **full Nimbusware install** + compute-worker; **LAN/Tailscale required** (fo1773) | Optional extra nodes register to fleet; same mesh protocol, centralized queue |
| **Folder bulk grants** | Grant creates invite/access rows; guest joins on **next open** of join link / session list | Grant + IAM role sync; participants appear when directory user next opens session |
| **Invite mechanism** | Signed URL `…/maker/app/#/chat/join/{token}` | In-app directory picker + optional email ping |
| **External collaborators** | Host opt-in `NIMBUSWARE_CHAT_ALLOW_EXTERNAL_INVITES=1` | Tenant policy `allow_external_collaborators` (default **false**) |
| **Public exposure** | Requires `NIMBUSWARE_API_HOST=0.0.0.0` + `NIMBUSWARE_PUBLIC_BASE_URL` | Ingress / Helm public URL |
| **Auth on join** | Create account or sign in (local) | API key or OIDC shell + session cookie |
| **Audit** | Local event log | IAM action log + `chat.participant.*` events |

### Data model (additive)

```sql
-- Human operator identity (Individual multi-user; Enterprise links tenant_id)
CREATE TABLE nimbusware_user (
  user_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  username TEXT NOT NULL,
  display_name TEXT NOT NULL DEFAULT '',
  email TEXT NULL,
  password_hash TEXT NULL,          -- Individual local auth; NULL when OIDC/API-key-only
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, username)
);

ALTER TABLE nimbusware_chat_session
  ADD COLUMN owner_user_id UUID NULL REFERENCES nimbusware_user(user_id),
  ADD COLUMN host_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  ADD COLUMN collaboration_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN workload_distribution TEXT NOT NULL DEFAULT 'host_only'
    CHECK (workload_distribution IN ('host_only', 'manual_claim', 'auto_share', 'auto_optimize')),
  ADD COLUMN folder_id UUID NULL,
  ADD COLUMN tags TEXT[] NOT NULL DEFAULT '{}';

CREATE TABLE nimbusware_chat_folder (
  folder_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  project_id UUID NULL,
  parent_folder_id UUID NULL REFERENCES nimbusware_chat_folder(folder_id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE nimbusware_user_group (
  group_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name)          -- tenant-wide groups (Enterprise directory aligned)
);

CREATE TABLE nimbusware_user_group_member (
  group_id UUID NOT NULL REFERENCES nimbusware_user_group(group_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  PRIMARY KEY (group_id, user_id)
);

CREATE TABLE nimbusware_chat_access_grant (
  grant_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  grantee_type TEXT NOT NULL CHECK (grantee_type IN ('user', 'group')),
  grantee_user_id UUID NULL REFERENCES nimbusware_user(user_id),
  grantee_group_id UUID NULL REFERENCES nimbusware_user_group(group_id),
  scope_type TEXT NOT NULL CHECK (scope_type IN ('folder', 'tag', 'session')),
  folder_id UUID NULL REFERENCES nimbusware_chat_folder(folder_id) ON DELETE CASCADE,
  tag TEXT NULL,
  session_id UUID NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  participant_role TEXT NOT NULL DEFAULT 'session_read',
  created_by UUID NOT NULL REFERENCES nimbusware_user(user_id),
  expires_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE nimbusware_session_role_claim (
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  run_id UUID NOT NULL,
  agent_role TEXT NOT NULL,
  claimed_by_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  node_id UUID NULL,                    -- set when execute_on=self + compute opt-in
  binding_snapshot JSONB NOT NULL,    -- claimer's model for this role at claim time
  claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  released_at TIMESTAMPTZ NULL,
  PRIMARY KEY (session_id, run_id, agent_role)
);

CREATE TABLE nimbusware_chat_session_participant (
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  participant_role TEXT NOT NULL CHECK (participant_role IN (
    'session_admin', 'session_write', 'session_read'
  )),
  invited_by UUID NULL REFERENCES nimbusware_user(user_id),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, user_id)
);

CREATE TABLE nimbusware_chat_invite (
  invite_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  participant_role TEXT NOT NULL DEFAULT 'session_read',
  expires_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL REFERENCES nimbusware_user(user_id),
  accepted_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL
);
```

### Turn model extension (align §20.28)

Extend `nimbusware_chat_turn.role` CHECK and `CHAT_TURN_ROLES`:

| Turn role | Author | Visible in thread as |
|-----------|--------|----------------------|
| `user` | Session owner | **You** (owner) — unchanged |
| `participant` | Invited human (`session_write` / `session_admin`) | **`display_name` (Guest)`** — new |
| `theater` | Agent pipeline | **`actor_display`** — unchanged |
| `system` | Platform | **System** — invite joined, role changed, model swap |

**Commentary vs interjection:**

- **Commentary** — `POST …/turns` with `role=participant`, `kind=commentary` → append-only thread line (peanut gallery banter).
- **Interjection** — `POST …/interjection-queue` (existing) authorized for `session_write`+ when session has active `run_id`; emits theater + optional `participant` turn quoting the steer text.

### Real-time sync

| Transport | Use |
|-----------|-----|
| **SSE session room** | `GET /v1/chat/sessions/{id}/stream` — fan-out theater lines + new turns to all participants |
| **Polling fallback** | `GET …/sessions/{id}?include_turns=true&since_ordinal=` for read-only clients |

Reuse existing Chat theater SSE wiring (`bindChatTheaterForRun`) but **multiplex** through session room so guests without Progress tab still see agent lines in the Chat thread.

## Track B — Epic program (fo1500–fo1589)

**Depends on:** §20.28 shipped (sessions, graph, fork, run cards). **Soft dependency** on Track A Phase A5 (fo1456 role claim) for write+ battery swap permissions.

### Phase B0 — Contract & ADR (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1500** | Normative §20.31 + ADR | `docs/adr/023-collaborative-chat-sessions.md` | Participant roles, edition matrix, non-goals |
| **fo1501** | Security review | Threat model: invite token leak, open LAN, guest interject | Documented mitigations |

### Phase B1 — Identity & auth (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1510** | `nimbusware_user` + auth | Local signup/signin API; session cookie for Maker | Individual multi-user on non-loopback |
| **fo1511** | Bootstrap owner | First launch creates owner user; migrates anonymous sessions | No lockout on upgrade |
| **fo1512** | Enterprise user link | Map IAM API key → `user_id`; OIDC claims → display_name | Enterprise chat knows “who” |
| **fo1513** | `require_user_access` upgrade | Replace loopback-open with authenticated user when collab enabled | Config flag preserves legacy localhost dev |
| **fo1514** | Public URL readiness | `NIMBUSWARE_PUBLIC_BASE_URL`, bind host warnings in Home wizard | Copy explains port-forward / firewall |

**Individual auth API (fo1510):**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/auth/signup` | Create local user (invite token may be required) |
| `POST` | `/v1/auth/signin` | Username/password → session cookie |
| `POST` | `/v1/auth/signout` | Clear session |
| `GET` | `/v1/auth/me` | Current user + tenant |

### Phase B2 — Session membership (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1520** | Participant CRUD | `GET/POST/DELETE …/sessions/{id}/participants` | Admin-only invite/revoke |
| **fo1521** | Invite tokens | `POST …/invites` → `{ join_url, expires_at }` | One-time or expiring links |
| **fo1522** | Join flow API | `POST /v1/chat/join` body `{ token }` → add participant | Creates user on signup if needed |
| **fo1523** | Role promotion | `PATCH …/participants/{user_id}` role change | Emits `system` turn |
| **fo1524** | Project scope | Invites scoped to `project_id`; guest sees project name only | No cross-project leakage |

### Phase B3 — Permission enforcement (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1530** | Turn authorization | `participant` turns require session_write+ | Read-only gets 403 on POST turns |
| **fo1531** | Interjection delegation | `session_write` may POST interjection when `run_id` linked | Audit `actor_user_id` on queue item |
| **fo1532** | Run start policy | `write_may_start_runs` session flag; default false | Owner enables per session |
| **fo1533** | Permission split | Trust slider → **session_admin** only; model swap + role claim → **session_write+** | fo1450/fo1456/fo1452 checks |
| **fo1534** | Fork/branch | Fork allowed for session_write+; read-only hidden | Matches §20.28 DAG rules |
| **fo1535** | **Workload distribution mode** | `PATCH …/sessions/{id}` `{ workload_distribution }`; Chat header control for admin | Default `host_only`; emits `workload.mode_changed` |
| **fo1536** | **Host identity** | `host_user_id` set on session create (= creator); shown in participant strip with ★ | Distinct from multi-admin |

### Phase B4 — Real-time & thread UX (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1540** | Session SSE room | `GET …/sessions/{id}/stream` | All participants see theater lines |
| **fo1541** | `participant` turn rendering | `chat.js` styling — distinct from owner `user` | `TURN_ROLE_LABELS.participant` |
| **fo1542** | Participant strip | Avatar row in Chat header | `data-testid="maker-chat-participants"` |
| **fo1543** | Read-only composer hide | Disable input + interjection ribbon for `session_read` | Peanut gallery watch mode |
| **fo1544** | Presence (optional MVP) | “3 watching” indicator via SSE heartbeat | No hard requirement for v1.2 ship |

#### fo1542 UI — Chat header participant strip

**Surface:** `#/chat` → top bar, right of session title.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Project: my-app / Chat session "Fix auth bug"          [Invite] [⋯]    │
│ Participants: (You · Admin) (alex · Write) (sam · Read) (guest · Read) │
└─────────────────────────────────────────────────────────────────────────┘
```

- **[Invite]** visible only for `session_admin`.
- **[⋯]** → Manage participants modal (promote/demote/revoke).

#### fo1521 UI — Invite modal

**Trigger:** Chat header **[Invite]** or Settings → Project → **Collaboration**.

```text
┌──────────────── Invite to group chat ─────────────────┐
│ Role for invitee:  (•) Read-only  ( ) Write  ( ) Admin │
│ Expires: [ 24 hours ▼ ]                                  │
│                                                          │
│ Individual:                                              │
│   Join link: https://host:8765/v1/maker/app/#/chat/join/…│
│   [ Copy link ]                                          │
│                                                          │
│ Enterprise:                                              │
│   Search org: [ _____________ ]  (directory typeahead) │
│   Or email (if external allowed): [ _____________ ]      │
│                                                          │
│                              [ Cancel ]  [ Create invite ]│
└──────────────────────────────────────────────────────────┘
```

**Enterprise directory disabled** when `allow_external_collaborators: false` — search org users only; no raw email field.

#### fo1522 UI — Join page

**Route:** `#/chat/join/{token}` (`data-testid="maker-chat-join"`).

```text
┌──────────────── Join Nimbusware group chat ─────────────┐
│ You're invited to watch/participate in:                  │
│   Project: my-app · Session: "Fix auth bug"             │
│   Role: Write (comment + steer agents)                    │
│                                                          │
│ Create account on this instance:                        │
│   Display name: [ _____________ ]                       │
│   Username:     [ _____________ ]                       │
│   Password:     [ _____________ ]                       │
│                                                          │
│ Already have an account? [ Sign in ]                      │
│                                                          │
│ [ ] Share my compute with this session (fo1741)           │
│ [ ] Allow host to manage my compute when I opt in (fo1786)│
│                                                          │
│                              [ Join session ]             │
└──────────────────────────────────────────────────────────┘
```

After join → redirect `#/chat?session_id=` with participant permissions applied.

#### fo1543 UI — Read-only peanut gallery

- Composer `textarea` hidden; show muted banner: “You’re watching as read-only. Ask the host for Write access to comment.”
- Theater SSE **on** — full agent group chat visible.
- Run card **expanded by default** for guests (they have no Progress tab habit).

### Phase B5 — Enterprise directory & policy (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1550** | Org user directory | `GET /v1/enterprise/users?q=` — display_name, user_id | Admin Console seed + OIDC sync hook |
| **fo1551** | Tenant collab policy | `allow_external_collaborators`, `max_session_participants`, **`host_transfer_consent_hours` (default 24)** | Admin Config → Collaboration tab |
| **fo1552** | Invite audit | IAM actions: `chat.invite.created`, `chat.participant.joined` | Enterprise audit export |
| **fo1553** | Host transfer note | Document: collab sessions + **timed host transfer** fo1780–fo1784; artifact bundle protocol | Supersedes “no migration v1.2” |

#### fo1551 UI — Admin Collaboration policy

**Route:** Admin `#/config` → **Collaboration** tab (`data-testid="admin-config-collaboration"`).

```text
┌──────────────── Tenant collaboration policy ────────────┐
│ [ ] Allow external collaborators (email/link outside org)│
│ Max participants per session: [ 20 ]                     │
│ Host transfer consent window: [ 24 ] hours               │
│ Default invite role: [ Read-only ▼ ]                     │
│ [ ] session_write may start runs (default off)           │
│ Allowed invite creators: [ session_admin only ▼ ]        │
└──────────────────────────────────────────────────────────┘
```

### Phase B6 — Settings & project UI (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1560** | Project → Collaboration | `#/settings` section: default invite role, collab on/off | Per-project override |
| **fo1561** | Home readiness row | “Public access” — URL reachable, TLS hint, port check | Links to docs |
| **fo1562** | Session sidebar | Session list shows participant count badge | `GET /chat/sessions` extended |

### Phase B7 — Quality & docs (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1570** | E2E journeys | Owner invites read-only guest; write guest interjects; enterprise directory invite | `tests/e2e/web/` |
| **fo1571** | OpenAPI + MCP | Document join/participant routes; optional MCP `nimbusware_chat_invite` | schema.d.ts regen |
| **fo1572** | Operator doc | `docs/collaborative-chat.md` — Individual port-forward runbook | Linked from Home |
| **fo1573** | Update boundary doc | `docs/integrations-external-chat.md` — peanut gallery vs webhook | No product scope creep |

### Phase B8 — Conversation library (folders, groups, tags) (2 sprints)

**Scope:** organize **many chat sessions** per project; bulk invite / ACL without merging sessions into one thread. Each session remains **one shared conversation** — sharing is still per session, but operators need not invite one-by-one.

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1574** | ADR 023 extension | Folder / group / tag ACL model in ADR 023 | No cross-tenant grants |
| **fo1575** | Schema | `nimbusware_chat_folder`, `nimbusware_user_group`, `nimbusware_chat_access_grant` | Migrations |
| **fo1576** | Folder + tag API | `GET/POST/PATCH/DELETE /v1/chat/folders`; move session; tag CRUD on session | OpenAPI |
| **fo1577** | Group API | `GET/POST …/groups`, membership CRUD | Enterprise + Individual |
| **fo1578** | Access grants + bulk invite | `POST …/access-grants`; bulk invite; **ACL merge: highest role at finest grain** | Emits `chat.access.granted` |
| **fo1579** | **Chat library sidebar** | Folder tree + tag filter + session list | `data-testid="maker-chat-library"` |
| **fo1580** | **Invite modal v2** | Tabs: Single session · Group members · Folder access · Tag access | fo1521 extension |
| **fo1581** | **Manage access panel** | View/revoke grants by folder/tag/group/user | session_admin |
| **fo1582** | E2E | Folder grant → all group members join new session in folder | `tests/e2e/web/` |

#### fo1579 UI — Chat library sidebar

**Surface:** `#/chat` left rail (collapsible).

```text
┌─ Conversations ─────────────────────┐
│ [ + Folder ]  [ + Group ]  [ Filter ]│
│ ▼ Engineering                        │
│   ▼ Q2 patches                       │
│     ● Fix auth bug          [write]  │
│     ○ Refactor billing      [read]   │
│   ▶ Campaign work                    │
│ Tags: [security] [frontend]            │
│ Groups: Platform · Security reviewers│
└──────────────────────────────────────┘
```

- Drag session into folder; multi-select tag apply.
- Badge shows **effective session role** = max role across grants at **finest scope** (session &gt; folder &gt; tag). Example: folder **read** + session **write** → **write** for that session only.

#### ACL precedence (normative)

| Scope (finest wins for role merge) | Example |
|------------------------------------|---------|
| **session** | Direct invite or session grant → overrides folder/tag for that session |
| **folder** | All sessions in folder unless session-specific grant differs |
| **tag** | Weakest default across tagged sessions |

**Effective role** = `max(session_role, folder_role, tag_role)` where each is compared by privilege (`session_admin` &gt; `session_write` &gt; `session_read`).

#### Bulk grant delivery — Individual vs Enterprise

| Edition | When grant applies | Guest experience |
|---------|-------------------|------------------|
| **Individual** | Rows created immediately; session **live** only while **host API** is up | Guest sees session on **next open** of Chat library / join link (fo1580 sends link or in-app notification) |
| **Enterprise** | IAM + participant rows on tenant Postgres | User sees session on next login to tenant Maker; **no laptop host required** |

**Default:** folder grant checkbox **“Apply to existing sessions”** = **off** (new sessions only); **“Auto-grant future sessions in folder”** = **on**.

#### fo1580 UI — Invite modal v2 (bulk ACL)

```text
┌──────────────── Share access ────────────────────────────┐
│ [ Single session ] [ Group ] [ Folder ] [ Tag ]            │
├────────────────────────────────────────────────────────────┤
│ Folder: [ Q2 patches ▼ ]                                   │
│ Grant to: (•) Group [ Platform ▼ ]  ( ) User [ search ]    │
│ Role: [ Write ▼ ]   Expires: [ never ▼ ]                   │
│ [✓] Apply to existing sessions in folder                   │
│ [✓] Auto-grant future sessions created in this folder      │
│                              [ Cancel ]  [ Grant access ]  │
└────────────────────────────────────────────────────────────┘
```

**Tag tab:** grant `session_read` on all sessions tagged `security` to group **Security reviewers**.

**Single session tab:** unchanged fo1521 join-link flow — **one conversation at a time**.

---

## Cross-track — Workload assignment, battery claim & parallel workflows

When a collaborative session runs a workflow, **parallel agent roles** (writer group, critic group) can be **split across participants** while the host still owns merge, gates, and theater. This combines Track A (per-role batteries), Track B (write+ permissions), and Track D (compute mesh) into two operator-visible modes plus a default.

### Mental model

```text
  Workflow (one run)                    Participants
  ┌─────────────────────┐              ┌──────────────────────────┐
  │ plan (host only)    │              │ Host ★ @owner (1 host)    │
  │ parallel_group:     │   manual     │  · merge + canonical API   │
  │   writers ×3        │ ──claim──►   │ Admins (invite/kick): N   │
  │   critics ×3        │   or auto    │ Guest write+ (alex)         │
  └─────────────────────┘ ──share──►   │  · claims Writer B + battery│
                                        │ Guest write+ (sam)         │
                                        │  · auto-assigned Critic 1  │
                                        └──────────────────────────┘
```

**One run, one workflow profile** — v1.2 does **not** merge unrelated workflow YAMLs in a single run. “Combining workflows” means **combining parallel stage slots** from the active workflow across humans/machines.

### Resolved product decisions (Jun 2026)

| Topic | Decision |
|-------|----------|
| Multiple runs per session | **One active run** per session; parallel slots split across users only |
| Concurrent claims | **Unlimited** per user; UI **warns** when claimer free compute &lt; others’ spare headroom (fo1785) |
| Guest lacks host model | Slot **stays on host** with **host bindings** — not guest best-effort. After **host transfer**, new host uses **their** best available |
| Remote execution | **Always `execute_on: self`** on claimer’s machine — **never** host-running guest cloud keys |
| Claim handoff | In-flight stage **finishes on prior executor**; next unit on claimer; claimer may **terminate & restart** early (fo1782) |
| Admin vs claim-only | Default **claim-only**; guest must opt in to **`allow_host_resource_management`** for host to pick bindings in guest env (fo1786) |
| Auto optimize | **`auto_optimize`** mode: Nimbusware routes agents across all opted-in nodes (requires default share + permissions) |
| API keys | **Never transmitted** between users — each battery uses executor’s local Model Hub vault only |
| Host transfer | **Admin↔admin only**; bidirectional (admin→admin or **current host→admin**); target non-admin **auto-promoted on accept**; **bundle import** to new machine Postgres (recommended install) + **conversation-scoped freeze** during cutover (fo1780–fo1784) |
| Host transfer consent | **Tenant-configurable**; default **`consent_expires_at` = 24 hours** (fo1551 / fo1781) |
| Declined / expired transfer | Requester **keeps** existing participant role (e.g. admin) |
| ACL precedence | **Highest role at finest grain** (session &gt; folder &gt; tag) |
| Folder bulk grant | **Existing sessions off by default**; Individual = **next open**; Enterprise = centralized IAM |
| User groups | **Tenant-wide** (`UNIQUE (tenant_id, name)`) |
| Guest worker install | **Full Nimbusware install** v1.2; doc **minimal worker agent** design for future (fo1713 / fo1773) |
| Network (Individual mesh) | **LAN/Tailscale required** — no generic NAT relay in v1.2 |
| Subscription providers | Model Hub **subscription-style** connections (ChatGPT sub, etc.) alongside API keys — user machine only |
| Remote tool execution | Agent tools/sandbox **always on guest worker** with host workspace snapshot — never host-side inference for claimed role |
| Auto optimize weights | Host **drag-and-drop priority** UI; default **recommended weighted mix**; **persist last-used weights per user** (fo1788) |
| Delegate control scope | **Per session** only (fo1786) |

### Per-user batteries (no secret sharing)

Each participant’s **battery** is a binding resolved on **that user’s machine**:

| Battery type | Stored where | Visible to others |
|--------------|--------------|-------------------|
| Ollama local model | Claimer’s Ollama | Model **name** + pull CTA in popover (fo1459) |
| Cloud API (Claude, ChatGPT, …) | Claimer’s Model Hub vault | Provider label + “configured ✓/○” in delegate panel only — **never key material** |

Example: host has ChatGPT only; guest has Claude API on their laptop. Guest claims **Security Critic** and selects **Claude** as battery → inference runs on **guest’s worker** using **guest’s vault**. Host sees `Sec.Critic · claude-sonnet-4 · @sam · sam-mac` in theater.

### Mode A — Manual claim (write+)

1. Session admin may set `workload_distribution: manual_claim` (optional — claims work in any non-`host_only` mode).
2. Guest with **session_write+** opens Agents strip on the active run card.
3. Clicks **Claim** on an eligible parallel role (writers/critics only).
4. Picks a battery from **their** Model Hub (local Ollama + their API connections).
5. Requires **Share compute** opt-in (fo1740) — execution is **always on claimer’s node**.
6. **Handoff:** if role was running on host, **current stage completes on host**, then migrates (fo1782); claimer may **Terminate & restart on me**.
7. Emits `workload.role_claimed` + theater line.

**Release / reassign:** claimer or session_admin releases; admin reassign → inherited after stage ends or forced restart per fo1782.

### Mode B — Auto share (session_admin + guest opt-in)

1. Session admin sets `workload_distribution: auto_share`.
2. Guests opt in to **Share compute** on join (fo1741) or later.
3. `MeshScheduler` assigns parallel units to opted-in nodes.
4. Worker uses guest battery **only when** role model/provider is satisfiable from guest catalog.
5. If guest **cannot** run with required binding → unit **stays on host** with **host settings** (fo1732).
6. After **host transfer** to that guest, step 5 switches to **new host best available** on their machine.

### Mode C — Auto optimize (“everyone share by default”)

1. Session admin sets `workload_distribution: auto_optimize` + session policy **`default_share_compute: true`**.
2. Guests default opt-in to share (override per user in Settings fo1752).
3. Guests may grant **`allow_host_resource_management`** (**per session**) so host can use **Accessible compute** (fo1787).
4. **Optimizer (fo1788):** default **recommended weighted mix** (headroom, model fit, latency, cost). **Host** may override via **drag-and-drop priority** UI; weights saved as **`user_optimizer_weights`** (last-used prepopulates next open).
5. Without delegate permission, nodes remain **claim-only** even in auto_optimize.

#### fo1788 UI — Optimizer weights (session_admin / host)

```text
┌─ Routing priority (drag to reorder) ─────────────────────┐
│ 1. ▣ Free compute headroom                               │
│ 2. ▣ Model / role fit                                    │
│ 3. ▣ Latency (LAN proximity)                             │
│ 4. ▣ Cost hint                                           │
│ [ Reset to recommended ]   [ Save as my default ]        │
└──────────────────────────────────────────────────────────┘
```

### Remote execution — tool jail (normative)

When a role runs on a **guest worker**, **all** LLM calls and **agent tool/sandbox** execution occur on the guest machine inside the existing jail. Host sends **read-only workspace snapshot** + bounded context packet only; merged patches return as artifacts. **No** host-side inference or tool runs for that role while claimed remotely.

### Binding + execution matrix

| Action | Permission | Runs on | Binding source |
|--------|------------|---------|----------------|
| Claim role | write+ | **Claimer node only** | Claimer’s Model Hub |
| Swap battery on claimed role | write+ (claimer) or admin w/ delegate | Claimer node | Claimer’s vault |
| Auto-share assignment | system | Opted-in node if model fits; else **host** | Executor or host respectively |
| Admin delegate binding | admin + guest delegate opt-in | Guest node | Admin picks from guest **metadata catalog** |
| Host transfer complete | admin (new host) | New host machine | New host best available |

### Resolution interaction (Track A)

Claim snapshot is **priority 1** in the resolver table. Resolution runs on the **executor machine** for remote units. Host never receives guest API secrets — work units carry `executor_user_id` + optional non-secret binding hints only.

---

# Track D — Distributed resource sharing (compute mesh)

## Problem statement (gap vs shipped)

Agents already exchange **bounded packets** (plan JSON, `SliceContextPacket`, critic verdicts, test logs) — not whole-repo prompts (§20.9, fo154, Lane M). Parallel execution today is **single-host only**:

| Capability | Location | Limit |
|------------|----------|-------|
| Parallel writer group | `writers.py`, `parallel_group: writers` in workflows | `asyncio.gather` on **one** machine |
| Parallel critics | `parallel_critics_enabled`, `lifecycle_verify.py` | Same host; gated by `hardware_tier=strong` |
| Redis fleet worker | `run_dispatch.py`, `run_worker.py`, fo205 | Enterprise **verify** queue — not LLM writer/critic stages; not tied to chat sessions |
| Resource governor | `nimbusware_hw.governor` | Caps parallel stages locally — no remote capacity |
| Hardware fleet API | `GET /platform/hardware`, Admin fleet table | Probe only — **no work assignment** |
| Track B (planned) | Collaborative session | Humans co-watch — **no compute contribution** from guest machines |

**Gap:** when multiple people join a session (Track B), their GPUs/CPUs sit idle while the host runs all parallel stages sequentially or locally parallel only.

## North star (Track D)

**Host-centric mesh:** the **session host** (project owner machine or Enterprise API pod) remains the **system of record**:

- Postgres **event store** (append-only findings, gate decisions, theater)
- **Project workspace** (git/snapshot authority)
- **Chat thread** + run cards (Track B)
- **Merge point** for all agent outputs

**Worker nodes** (collaborator machines that opt in) execute **isolated stage units** and return **structured results** only. The host scheduler assigns work from **parallelizable** stage groups when remote capacity is available.

```text
                    ┌──────────────── Host (canonical) ────────────────┐
                    │  API · Postgres events · workspace · Chat UI   │
                    │  Scheduler · merge · gates · theater SSE       │
                    └───────────┬──────────────────────┬───────────────┘
                                │                      │
              SliceContextPacket│                      │results + telemetry
                                ▼                      ▼
                    ┌───────────────────┐    ┌───────────────────┐
                    │ Worker node A      │    │ Worker node B      │
                    │ (guest GPU)        │    │ (guest CPU)        │
                    │ implementation     │    │ security_critic    │
                    │ LLM + tools jail   │    │ LLM JSON verdict   │
                    └───────────────────┘    └───────────────────┘
```

**Not** a peer-to-peer git mesh or multi-master event store — workers are **stateless executors**; host validates, merges, and gates.

### Parallelizable work units (v1.2 scope)

Derived from shipped stage graph + workflow YAML:

| Unit kind | Stage keys | Parallelism rule | Remote OK when |
|-----------|------------|------------------|----------------|
| **Writer group** | `implementation`, `test_writer`, `frontend_writer` | Same `parallel_group: writers` after `plan` | Each writer gets disjoint packet; workspace patch returned as unified diff artifact |
| **Critique group** | `security_critic`, `performance_critic`, `network_resilience_critic` | `parallel_critics` when enabled | Read-only scan inputs + JSON verdict; no workspace write |
| **Verifier fan-out** (stretch) | Subprocess verify shards | Existing Redis dispatch steps | Enterprise only; host merges logs |
| **Explicitly sequential** | `plan`, `slice.plan`, `slice.implement`, gates, stitch, integrator | Must run on **host** | Strong consistency / workspace lock |

Campaign **slice chain** stays host-orchestrated; optional future epic assigns **independent campaign ticks** across nodes (out of v1.2 ship).

### Agent I/O contract (remote execution)

Reuse existing artifacts — remote executor is a **transport**, not a new agent model:

```yaml
# Envelope: host → worker (POST /v1/compute/nodes/{id}/execute or pull from queue)
work_unit:
  work_unit_id: uuid
  run_id: uuid
  session_id: uuid | null
  stage_name: implementation.critique | implementation | …
  agent_role: backend_writer
  executor_user_id: uuid           # claimer or auto-share assignee
  model_binding: { … }           # optional snapshot; worker may resolve from executor profile
  context_packet:                 # fo154 caps — diff excerpt, test log, plan JSON
    max_chars: 16000
    payload: { … }
  workspace_snapshot_ref: host://snapshots/{id}  # read-only tree or patch base
  tool_policy: agent_sandbox       # same jail caps as local JIT loop
  timeout_seconds: 120

# Envelope: worker → host (callback POST …/work-units/{id}/complete)
work_result:
  work_unit_id: uuid
  status: ok | failed | timeout
  events: [ … ]                    # projected StageStarted/Passed or CriticVerdict payloads
  token_hints: { prompt_tokens, completion_tokens }
  executor_node_id: uuid
  error: string | null
```

Host **replays** returned events into `event_store` after schema validation — same as local orchestrator paths.

## Architecture — compute mesh

```text
┌──────────────── Chat / Progress / Settings ─────────────────────────────┐
│  Connected nodes strip · share toggle · stage→node assignment view       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  Host API                                                                │
│  GET  /v1/compute/mesh/status                                           │
│  POST /v1/compute/nodes/register · heartbeat                            │
│  POST /v1/chat/sessions/{id}/compute/opt-in                             │
│  Scheduler: MeshScheduler.assign(parallel_group) → node_id              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  InMemoryMeshQueue    Redis mesh queue     Enterprise fleet-worker
  (Individual LAN)     (session-scoped keys)  (fo205 extension)
        │                    │                    │
        └────────────────────┴────────────────────┘
                             │
                    nimbusware-compute-worker
                    (poetry run nimbusware-compute-worker --host-url … --token …)
```

### Node registry (normative)

```sql
CREATE TABLE nimbusware_compute_node (
  node_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  session_id UUID NULL REFERENCES nimbusware_chat_session(session_id),
  user_id UUID NULL REFERENCES nimbusware_user(user_id),
  display_name TEXT NOT NULL DEFAULT '',
  host_label TEXT NOT NULL DEFAULT '',          -- e.g. "alex-laptop"
  base_url TEXT NOT NULL,                       -- worker callback reachability (LAN/Tailscale)
  capabilities JSONB NOT NULL DEFAULT '{}',     -- tier, gpus, models[], max_parallel
  share_policy TEXT NOT NULL DEFAULT 'off',     -- off | claim_only | managed_by_host | full_auto
  allow_host_resource_management BOOLEAN NOT NULL DEFAULT FALSE,
  last_heartbeat_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'unknown'        -- online | degraded | offline
);
```

**Individual:** nodes register against host API with invite-scoped **`compute_token`**. Reachability: **LAN or Tailscale only** in v1.2 (document in fo1773; Home readiness warns if mesh enabled without tailnet).  
**Enterprise:** nodes may be **fleet workers** (existing Redis) **or** session-scoped guest nodes; Admin sees both. Collab mesh is **optional** — default path is centralized fleet compute.

### Scheduling policy

| Policy | Behavior |
|--------|----------|
| **host_only** | All parallel units on host (default) |
| **manual_claim** | Remote only for claimed roles on claimer node |
| **auto_share** | Scheduler → opted-in nodes when model fits; else **host bindings on host** |
| **auto_optimize** | Optimizer routes across opted-in + delegate-capable nodes | 
| **spread** (sub-policy) | Assign each member of `parallel_group` to distinct online nodes; overflow → host |
| **pack** (sub-policy) | Fill one powerful node up to `max_parallel` before next |
| **cap** | Never assign more than `N` remote units per run slice (config) |

Scheduler respects **ResourceGovernor** on host **and** reported `capabilities.max_parallel` per node. Host never sends workspace **write** to more than one node for the same slice concurrently (patch merge on host).

## Track D — Epic program (fo1700–fo1799)

**Hard dependency:** Track B fo1510+ (user identity), fo1520+ (session participants). **Soft dependency:** Track A fo1421 (model binding on remote nodes).

### Phase D0 — Contract & audit (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1700** | ADR 025 + §20.32 | `docs/adr/025-distributed-compute-mesh.md` | Host-authoritative merge; threat model |
| **fo1701** | Parallel inventory | Matrix: every `parallel_group` / `parallel_critics` / dispatch step → remote eligibility | Signed off in ADR |

### Phase D1 — Node registry & worker agent (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1710** | Schema + migrations | `nimbusware_compute_node`, `nimbusware_work_unit` tables | `postgres.sql` |
| **fo1711** | Register + heartbeat API | `POST /v1/compute/nodes/register`, `POST …/heartbeat` | Node online/offline projection |
| **fo1712** | Capabilities probe | Worker reports hardware tier, Ollama models, governor limits | Same fields as `GET /platform/hardware` |
| **fo1713** | **`nimbusware-compute-worker`** CLI | Long-lived agent on **full install**; heartbeat, pull/listen, execute locally | Package in monorepo |
| **fo1713b** | Minimal worker design doc | `docs/compute-mesh.md` § “Future minimal worker agent” — footprint, sync protocol | Not v1.2 ship code |
| **fo1714** | Auth | `compute_token` from session invite; Enterprise API key variant | No host admin token on worker |

### Phase D2 — Execution protocol (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1720** | Work unit queue | Host enqueue/dequeue/ack; session-scoped Redis keys `{session_id}:mesh:queue` | At-least-once + idempotent merge |
| **fo1721** | `RemoteStageExecutor` | Executes one stage unit locally on worker using existing orchestrator role handlers | Parity test vs host-local |
| **fo1722** | Result ingest | Host `complete_work_unit` validates + appends events | Duplicate completion ignored |
| **fo1723** | Model binding on worker | Worker resolves LLM via claimer’s Model Hub / Ollama; work unit carries `executor_user_id` | Track A fo1457; auto-share path |

### Phase D3 — Scheduler integration (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1730** | `MeshScheduler` | Hook `_run_writers_parallel_dispatch` — respect **manual claims** + **auto_share** mode | Claimed roles pinned; unclaimed → spread |
| **fo1731** | Parallel critics remote | `lifecycle_verify.py` critique fan-out to mesh | Same gate merge on host |
| **fo1732** | Overflow & fallback | Guest lacks model → **host node + host bindings**; remote fail → retry; theater line | No silent drop |
| **fo1733** | Governor mesh caps | `max_remote_work_units`, RAM pressure → host-only | Mid-run degrade events |
| **fo1734** | Claim-aware routing | Claims pin executor; handoff after stage boundary | fo1456 + fo1782 |
| **fo1735** | **Compute headroom warnings** | On multi-claim: compare claimer free slots vs peers; non-blocking UI toast | fo1785 UI |

### Phase D4 — Session mesh (Track B glue) (1–2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1740** | Session opt-in API | `POST /v1/chat/sessions/{id}/compute/opt-in` body `{ enabled, share_policy }` | Links `user_id` → `compute_node` |
| **fo1741** | Join flow extension | Join page checkbox: “Share compute with this session” | Default **off** |
| **fo1742** | Revoke | Participant removed → node deregistered; in-flight units cancelled | fo1520 revoke path |
| **fo1743** | Host-only roles | `session_read` cannot register workers or claim roles; write/admin may opt-in + claim | Permission matrix |
| **fo1744** | **Auto-share scheduler path** | When `workload_distribution=auto_share`, assign parallel units to opted-in nodes without claim rows | fo1746 model coverage |
| **fo1745** | **Manual-claim scheduler path** | When `manual_claim`, only claimed roles go remote; others stay on host | fo1734 |
| **fo1746** | Participant model coverage | Worker reports satisfiable roles; auto-share skips guest when no match | Host fallback fo1732 |
| **fo1747** | Admin force host-only | Mid-run mode → `host_only` cancels remote queue | fo1742 pattern |

### Phase D5 — Operator UI (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1750** | Chat **Nodes** strip | Beside Participants: host + workers + **claimed roles** per user | `data-testid="maker-chat-compute-nodes"` |
| **fo1751** | Progress assignment view | Gate summary + “Ran on: alex-laptop (implementation)” + claimer badge | Extends role telemetry |
| **fo1752** | Settings → **Compute sharing** | Default opt-in; workload mode default; spread/pack | Individual + Enterprise |
| **fo1753** | Theater lines | `compute.assigned`, `compute.completed`, `workload.role_claimed` | Visible in Chat thread |
| **fo1754** | **Workload mode control** | Host only · Manual claim · Auto share · **Auto optimize** | fo1535 UI |
| **fo1755** | Join flow copy | Explain auto share vs manual claim when admin enables collab | fo1741 extension |

#### fo1750 UI — Connected nodes strip (Chat)

**Surface:** `#/chat?run_id=` → header row under Participants.

```text
Compute:  [★ Host · RTX 4060 · 2 active] [alex · Write · GPU · Writer B claimed]
          Mode: Manual claim ▼   Policy: Spread ▼   [Invite compute…]
```

- **Host** always listed (star); shows local governor load.
- **Guest workers** only when opted-in + heartbeat fresh (&lt; 30s).
- **Claimed roles** shown on participant chip when `manual_claim`.
- **Workload mode** dropdown (**session_admin** only): Host only · Manual claim · Auto share · **Auto optimize**.
- **Invite compute…** (session_admin): copy worker install one-liner:
  `poetry run nimbusware-compute-worker --host-url https://… --session-token …`

#### fo1752 UI — Settings → Compute sharing

**Route:** `#/settings` → **Compute sharing** (`data-testid="maker-settings-compute-sharing"`).

```text
┌──────────────── Compute sharing ──────────────────────────────────────┐
│ Default when joining others' sessions:  [ ] Share my compute            │
│ Default for my sessions (guests):       [✓] Allow guests to offer GPU   │
│ Default workload mode for new sessions: [ Manual claim ▼ ]              │
│ [ ] Default share compute for new joiners (auto optimize)               │
│ Scheduling policy (auto share / optimize):  (•) Spread  ( ) Pack        │
│ Max remote nodes per session: [ 4 ]                                     │
│ Require same project network (LAN/Tailscale): [✓]                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase D6 — Enterprise & fleet unification (1 sprint)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1760** | Fleet worker as mesh node | Existing `run_dispatch_worker.py` registers as enterprise compute node | fo205 runbook updated |
| **fo1761** | Admin **Fleet → Mesh** panel | Session + fleet nodes; queue depth; opens **Accessible compute** drawer | fo1787 |
| **fo1762** | Tenant policy | `allow_guest_compute`, `max_mesh_nodes`, `default_share_compute` | Admin Collaboration tab (fo1551) |
| **fo1763** | **Accessible compute drawer** | Side panel: machines admin may route to; metadata-only battery catalog per node | `data-testid="maker-accessible-compute"` |

#### fo1763 / fo1787 UI — Accessible compute (session_admin / host)

**Surface:** Chat or Progress → **[Accessible compute]** (admin only when ≥1 delegate-capable node).

```text
┌─ Accessible compute ─────────────────────────────────────────┐
│ Host ★ this-machine · RTX 4060 · 3/8 free · ChatGPT ✓         │
│ alex-mac · GPU · 6/8 free · Ollama: qwen, llama · Claude ✓     │
│   [ Assign Writer B → qwen2.5-coder:14b ]  [ Request control ] │
│ sam-laptop · CPU · 1/4 free ⚠ low headroom · OpenAI ✓         │
│   Claims: Sec.Critic (running…)  [ View only — claim-only ]    │
└────────────────────────────────────────────────────────────────┘
```

- **Request control** → guest prompt to grant `allow_host_resource_management` (fo1786).
- With delegate: admin selects agent role + binding from guest’s **metadata catalog** (model names, provider booleans — no keys).
- **⚠** when assigning to low headroom node (fo1785).

### Phase D7 — Security & quality (1–2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1770** | Sandbox on worker | Agent tools jail; no host `.env`; packet caps | Same as `agent_sandbox.md` |
| **fo1771** | **No cross-user secrets** | Work units never carry API keys; delegate panel metadata only | Security review sign-off |
| **fo1772** | E2E two-machine | Manual claim + auto share + delegate path | `test_compute_mesh_journey.py` |
| **fo1773** | Doc | `docs/compute-mesh.md` — **LAN/Tailscale**, full install worker, host transfer, **future minimal worker** | Linked from fo1750 |

### Phase D8 — Host transfer, handoff & delegate control (2 sprints)

| # | Epic | Deliverable | Exit criteria |
|---|------|-------------|---------------|
| **fo1780** | **Host transfer request** | `POST …/host-transfer` — **bidirectional**: (a) session_admin → become host, (b) **current host → another admin**; target non-admin → **promote on accept** | Emits `host.transfer.requested` |
| **fo1781** | **Timed consent (Postgres)** | `consent_expires_at` from tenant policy (**default 24h**); `artifact_transfer_expires_at` optional extension | Decline/expired → requester keeps role |
| **fo1782** | **Claim handoff + early restart** | Finish current stage on prior executor OR claimer `POST …/work-units/{id}/terminate-restart` | fo1456 migration |
| **fo1783** | **Artifact bundle protocol** | Export/import **conversation-scoped** slice: session rows, event tail, claim map, workspace snapshot refs; new host runs **`recommended` install Postgres** + import | Checksum + resume |
| **fo1784** | **Become host** | **Conversation-scoped freeze** during cutover; `host_user_id` updates; new host API canonical; old host read-only for that session until complete | fo1781 completed |
| **fo1785** | Compute headroom UI | Warn on multi-claim / low headroom assignment | Non-blocking |
| **fo1786** | **Delegate control API** | `POST …/compute/delegate-control` — **per session** opt-in on join/settings | Host configures guest env |
| **fo1787** | Accessible compute drawer | fo1763 in Maker Chat + Progress | Playwright |
| **fo1788** | **Auto optimize scheduler + weights UI** | Weighted mix + drag priority; `user_optimizer_weights` persisted | fo1744 extension |
| **fo1789** | E2E host transfer | Two-machine transfer with timed consent + artifact verify | `test_host_transfer_journey.py` |

#### Host transfer consent (normative schema)

```sql
-- Tenant policy (Admin Collaboration tab fo1551)
-- host_transfer_consent_hours INT NOT NULL DEFAULT 24

CREATE TABLE nimbusware_host_transfer_request (
  transfer_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id),
  project_id UUID NOT NULL,
  from_host_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  to_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  initiated_by_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  direction TEXT NOT NULL CHECK (direction IN ('admin_requests_host', 'host_nominate_successor')),
  promote_to_admin BOOLEAN NOT NULL DEFAULT FALSE,  -- set when to_user was not session_admin
  status TEXT NOT NULL CHECK (status IN (
    'pending', 'accepted', 'declined', 'expired', 'frozen', 'transferring', 'completed', 'cancelled'
  )),
  consent_expires_at TIMESTAMPTZ NOT NULL,
  artifact_transfer_expires_at TIMESTAMPTZ NULL,
  from_host_agreed_at TIMESTAMPTZ NULL,
  freeze_started_at TIMESTAMPTZ NULL,
  artifact_manifest JSONB NOT NULL DEFAULT '{}',
  completed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE nimbusware_user_optimizer_weights (
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id),
  weights JSONB NOT NULL,   -- ordered factors + numeric weights from last save
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, tenant_id)
);
```

**Flow (Individual):**

1. **session_admin** requests to become host **or** **current host** nominates another **session_admin** (fo1780).
2. If target is not admin → `promote_to_admin=true`; on accept, promote then transfer.
3. Current host sees **Accept / Decline** until `consent_expires_at` (**default 24h**, tenant `host_transfer_consent_hours`).
4. On accept → status **`frozen`**: **conversation-scoped** lock (session turns, claims, in-flight work units for that `session_id` only — not whole project).
5. New machine (already has Postgres from **recommended install** + preflight) receives **artifact bundle** → import into local Postgres + workspace paths.
6. Cutover → `host_user_id` = target; `host.transfer.completed`; freeze lifted on old host for that session.

**Declined / expired:** requester **unchanged** (stays session_admin if they were admin).

**Enterprise:** no laptop Postgres migration — update `host_user_id` to IAM user tied to **fleet coordinator role**; session rows stay in **tenant Postgres**; optional pod affinity change (fo1784 enterprise note).

---

## Combined build sequence

| Order | Phase | Track | Sprints | Unblocks |
|------:|-------|-------|--------:|----------|
| 1 | A0 + B0 + C0 + **D0** | All | 1–2 | ADRs + audits |
| 2 | **C1** | Installer | 1–2 | Recommended default |
| 3 | A1 + C2 | Models + vault | 2 | Providers + keys |
| 4 | A2 | Models | 2 | Resolver |
| 5 | C3 | Model Hub | 2 | Local + API UI |
| 6 | B1 | Collab identity | 2 | Users + invites |
| 7 | A3 | Models | 1 | Cloud preflight |
| 8 | B2–B3 | Collab | 3 | Session + permissions |
| 9 | **D1–D2** | **Mesh** | 3–4 | Node registry + work units |
| 10 | A4 + C3 + B4 | UI | 2–3 | Settings + Chat |
| 11 | A5 + B4 | Both | 2 | Model swap + participants |
| 12 | **D3–D4** | **Mesh** | 3–4 | Scheduler + session opt-in (**requires B2+**) |
| 13 | **D5** | **Mesh UI** | 2 | Nodes strip + Settings |
| 14 | B5 + **B8** + **D6** | Enterprise + library | 3–4 | Directory + folders/grants + fleet |
| 15 | A6–A8, B6–B7, C4, **D7–D8** | All | 3–5 | Ship gates + host transfer |

**Total:** ~28–34 sprints sequential; **D8** after **D4** + **B3**; **B8** after **B2**.

**Critical paths:**

- Models: C0 → C1 → A1/C2 → C3 → A4 → A5 (+ fo1459 popover)  
- Collab: B0 → B1 → B2 → B3 → B4 → **B8**  
- **Mesh: D0 → D1 → D2 → D3 → D4 → D5 → D7 → D8**

---

## Event model (combined audit trail)

| Event type | Track | When |
|------------|-------|------|
| `model.bindings.snapshot` | A | `run.created` |
| `model.binding.overridden` | A | Model swap |
| `chat.invite.created` | B | Invite link generated |
| `chat.participant.joined` | B | Guest accepts invite |
| `chat.participant.role_changed` | B | Promote/demote |
| `chat.participant.removed` | B | Revoke access |
| `chat.participant.commentary` | B | Optional mirror of participant turn for audit export |
| `provider.connection.updated` | C | API key saved/rotated/deleted in Model Hub |
| `ollama.bootstrap.completed` | C | Install/start from Model Hub or recommended profile |
| `install.profile.applied` | C | `barebones` or `recommended` + edition persisted to `.env` / config |
| `compute.node.registered` | D | Worker joined mesh |
| `compute.node.heartbeat` | D | Liveness + capability refresh |
| `compute.work_unit.assigned` | D | Stage dispatched to node |
| `compute.work_unit.completed` | D | Results merged on host |
| `compute.mesh.policy_changed` | D | spread/pack/host_only |
| `workload.mode_changed` | B/D | host_only / manual_claim / auto_share / auto_optimize |
| `workload.role_claimed` | A/D | write+ claims parallel role + battery |
| `workload.role_released` | A/D | claimer or admin releases role |
| `workload.handoff.scheduled` | D | stage boundary migration to claimer |
| `workload.terminated_restart` | D | claimer early restart on self |
| `host.transfer.requested` | B/D | new admin requests host role |
| `host.transfer.completed` | B/D | artifact bundle applied; new canonical host |
| `compute.delegate.requested` | D | host asks to manage guest env |
| `compute.delegate.granted` | D | guest opts in |
| `chat.access.granted` | B | folder/tag/group ACL applied |
| `chat.folder.created` | B | library organization |

---

## Preflight relaxation (Track A)

### Target

```yaml
preflight:
  required: true
  mode: role_coverage
  checks:
    - roles_covered
    - providers_reachable
  ollama:
    required_if_any_local_binding: true
```

| Scenario | Home / Wizard behavior |
|----------|------------------------|
| Ollama down, all roles cloud | **Ready** — “Cloud-only mode” |
| Ollama up, mixed | **Ready** — “Hybrid” |
| Ollama down, one role local | **Blocked** — list roles to fix or swap |
| Collab enabled, no public URL | **Warn** — “Invites will not work off-machine” (Track B fo1514) |

---

## External LLM provider notes (Track A)

| Provider | v1.2 scope |
|----------|------------|
| OpenAI / ChatGPT | fo1412, fo1612 |
| Anthropic / Claude | fo1412, fo1612 |
| Google Gemini | fo1603, fo1612 |
| xAI / Grok | fo1612 |
| OpenRouter / LiteLLM | fo1413, fo1612 |
| Cursor Composer | **Out of scope** — fo1613 IDE/MCP card only |
| Ollama | fo1411, fo1611 (install deferred from fo1593) |

---

## Success metrics

| Metric | Target |
|--------|--------|
| Fresh **recommended** install → preflight green (both models) | **< 25 min** documented (fo1595) |
| **Barebones** install → `nimbusware-run --quick` | **< 5 min** after Poetry (fo1593) |
| Individual vs Enterprise same profile flags | **100%** parity on Ollama/model steps (fo1596) |
| Save + probe API connection in Model Hub | **< 2 min** (fo1612) |
| Operator configures ≥3 agent roles with distinct models | **< 5 min** (fo1442) |
| Cloud-only install → first gate pass | **< 20 min** documented |
| Mid-chat model swap → next stage uses new model | **100%** fo1480 |
| Invite link → guest watching theater | **< 2 min** on LAN (fo1570) |
| Read-only guest blocked from interjection | **100%** API tests |
| Write guest steer appears in interjection queue | **100%** fo1570 |
| Enterprise external invite blocked by policy | **100%** when flag false |
| Session SSE delivers theater to 3 concurrent guests | **< 2 s** p95 latency |
| fo1310 + §20.28 journeys still pass | **100%** regression |
| Parallel writers on 2+ nodes → single gate on host | **100%** fo1772 |
| Remote worker failure → host local retry | **100%** fo1732 |
| Guest read-only cannot register compute | **100%** fo1743 |
| Write guest claims writer role → runs on guest node | **100%** fo1772 manual path |
| Auto share assigns critic to guest with local model | **100%** fo1744 |
| Claimed role uses claimer binding not host default | **100%** fo1457 |
| Guest without model → host bindings on host | **100%** fo1732 |
| Multi-claim headroom warning shown | **100%** fo1785 |
| Host transfer completes within consent window | **100%** fo1789 |
| Delegate panel shows zero secret fields | **100%** fo1771 audit |
| Folder grant → group member opens session | **100%** fo1582 |
| Click foreign model → Ollama pull queued | **100%** fo1460 |

---

## Non-goals (v1.2)

**Track C**

- Bundled **vLLM / llama.cpp server manager** — Ollama only for local
- **Auto-pull** largest model without confirm — operator confirms in Model Hub
- Cursor Composer as LLM backend (IDE card only)

**Track A**

- Cloud-only as **platform default**
- Cursor Composer as LLM backend
- Per-message model routing (per agent role only)

**Track B**

- **General chat product** — channels, DMs, reactions, threads beyond §20.28 DAG
- **Slack/Teams replacement** — use webhook for external tools; peanut gallery is session-scoped
- **Guest access to Admin Console** or config mutations
- **Cross-tenant** session joins
- **Video/voice** presence
- **Anonymous invite** without account creation (token-only view) — always authenticated user for audit

**Track D**

- **Multi-master** event store or workspace — host always merges
- **Arbitrary stage** remote execution — sequential stages stay on host
- **Cross-tenant** worker pools
- **P2P** discovery without host API — all workers register with host
- **Campaign slice parallelization** across nodes (defer post-v1.2)
- Shipping **host secrets** to workers (bindings snapshot only; keys on worker or env ref)
- **Cross-user API key** sync, export, or host-side storage of guest vault credentials

**Both**

- Replacing verifiers/gates
- Ungated factory or trust-10 without owner consent

---

## Cross-doc completion matrix

**Legend:** ☑ shipped MVP+ · ◐ partial / stub · — not applicable · ☐ not started

| Phase | Epics | Code | UI | Tests | Docs |
|-------|-------|------|-----|-------|------|
| C0 | fo1590–fo1592 | ☑ | — | ☑ | ☑ |
| C1 | fo1593–fo1598 | ☑ | ☑ | ☑ | ☑ |
| C2 | fo1600–fo1605 | ☑ | — | ☑ | ☑ |
| C3 | fo1610–fo1616 | ☑ | ☑ | ☑ | ☑ |
| C4 | fo1617–fo1620 | ☑ | ☑ | ☑ | ☑ |
| A0 | fo1400–fo1401 | — | — | ☑ | ☑ |
| A1 | fo1410–fo1414 | ☑ | — | ☑ | ☑ |
| A2 | fo1420–fo1424 | ☑ | — | ☑ | ☑ |
| A3 | fo1430–fo1433 | ☑ | ☑ | ☑ | ☑ |
| A4 | fo1440–fo1445 | ☑ | ☑ | ☑ | ☑ |
| A5 | fo1450–fo1462 | ☑ | ☑ | ☑ | ☑ |
| A6–A8 | fo1460–fo1483 | ☑ | — | ☑ | ☑ |
| B0 | fo1500–fo1501 | ☑ | — | ☑ | ☑ |
| B1 | fo1510–fo1514 | ☑ | — | ☑ | ☑ |
| B2 | fo1520–fo1524 | ☑ | ☑ | ☑ | ☑ |
| B3 | fo1530–fo1536 | ☑ | ☑ | ☑ | ☑ |
| B4 | fo1540–fo1544 | ☑ | ☑ | ☑ | ☑ |
| B5 | fo1550–fo1553 | ☑ | ☑ | ☑ | ☑ |
| B6–B7 | fo1560–fo1573 | ☑ | ☑ | ☑ | ☑ |
| B8 | fo1574–fo1582 | ☑ | ☑ | ☑ | ☑ |
| D0 | fo1700–fo1701 | ☑ | — | ☑ | ☑ |
| D1 | fo1710–fo1714 | ☑ | — | ☑ | ☑ |
| D2 | fo1720–fo1723 | ☑ | — | ☑ | ☑ |
| D3 | fo1730–fo1735 | ☑ | — | ☑ | ☑ |
| D4 | fo1740–fo1747 | ☑ | ☑ | ☑ | ☑ |
| D5 | fo1750–fo1755 | ☑ | ☑ | ☑ | ☑ |
| D6 | fo1760–fo1763 | ☑ | ☑ | ☑ | ☑ |
| D7 | fo1770–fo1773 | ☑ | — | ☑ | ☑ |
| D8 | fo1780–fo1789 | ☑ | ☑ | ☑ | ☑ |

**Partial notes:** B8 invite modal v2 tabs shipped (link / directory / group). D3 critics remote fan-out (fo1731) wired via `mesh_assign_parallel_critics`. D8 delegate-control API + optimizer weights UI shipped.

**Ship when:** Tracks C0–C3 + C4, A0–A5 + A8, B0–B8, D0–D8 complete for Individual + Enterprise collab/mesh MVP. Mesh writers + critics enqueue on non-`host_only` sessions; host still merges gate events.

---

## Relationship to existing epics

| Prior epic | v1.2 treatment |
|------------|----------------|
| **fo543–fo549** Model Manager | **Absorbed into Model Hub** fo1610–fo1611 (preset wizard retained) |
| **fo1310–fo1313** hybrid routing | Shim fo1471; UI → fo1442 + fo1612 connections |
| **§20.28** congruent Chat | Extended by Track B — **not replaced** |
| **§20.9** run theater / bounded packets | Fan-out fo1540; remote stages use same packets; merge on host |
| **fo712** rich group chat | Participant commentary adds human lines |
| **fo816–fo832** interjection | Delegated to session_write fo1531 |
| **fo201** Enterprise IAM | Extended fo1512, fo1550 |
| **fo205** Redis fleet worker | Extended as enterprise mesh node fo1760 |
| **fo535–fo541** hardware governor | Mesh caps fo1733; node capabilities fo1712 |
| **Track B** sessions | fo1740–fo1747 glue; compute opt-in + workload mode fo1535 |
| **Track A** claims + popover | fo1456–fo1462; fo1459 pull CTA |
| **Track B** library | fo1574–fo1582 folders/groups/tags |
| **Host transfer** | fo1780–fo1784 supersedes fo1553 no-migration note |

---

## Document map

| File | Role |
|------|------|
| **This file** | v1.2 program — fo1400–fo1799 (Tracks A–D) |
| `PLAN_GAP.md` | Active queue when program kicks off |
| `v1.1features.md` | Prior release ledger |
| `nimbusware-orchestrator-local-plan.md` | Add §20.30 (models), §20.31 (collab), §20.32 (mesh) on approval |
| `docs/adr/022-per-role-model-routing.md` | fo1400 |
| `docs/adr/023-collaborative-chat-sessions.md` | fo1500 + fo1574 library ACL |
| `docs/adr/026-host-transfer.md` | fo1780 (proposed) |
| `docs/conversation-library.md` | fo1582 |
| `docs/adr/024-install-profiles.md` | fo1593 |
| `docs/adr/025-distributed-compute-mesh.md` | fo1700 |
| `docs/collaborative-chat.md` | fo1572 |
| `docs/compute-mesh.md` | fo1773 |
| `docs/model-hub.md` | fo1619 |
| `docs/install-profiles.md` | fo1597 / fo1619 |
| `scripts/install_nimbusware.py` | fo1593–fo1598 |
| `scripts/runbooks/run_dispatch_fleet_runbook.md` | fo1760 update |

---

## v1.2 finish line (summary)

**Ship when:**

1. **Universal installer** — **`--install-profile recommended`** (default: Ollama + qwen + llama pull) and **`barebones`** (opt-in minimal); Individual and Enterprise differ by edition defaults only (fo1593–fo1598).
2. **Model Hub** — local Ollama install/list/pull + API connections vault (fo1610–fo1612).
3. **Model resolver** — all agent LLM calls through `ModelBindingResolver`; relaxed preflight (fo1430).
4. **Agent & Models Settings** — per-role bindings saved to user profile (fo1442).
5. **Mid-chat model swap & role claim** — write+ unlimited claims with headroom warnings; battery popover + Ollama pull (fo1452 + fo1456 + fo1459–fo1461).
6. **Collaborative sessions** — multiple **session_admins** + one **host**; invite link or org directory; folders/groups/tags (fo1520–fo1536, **fo1574–fo1582**).
7. **Peanut gallery UX** — read-only watch + write commentary/steer in Chat thread (fo1540–fo1543).
8. **Compute mesh MVP** — always `execute_on: self`; manual claim + auto share + auto optimize; Accessible compute drawer (fo1730–fo1788).
9. **Host transfer** — bidirectional admin↔admin; bundle import to new Postgres; conversation freeze; default 24h consent (fo1780–fo1784).
10. **Regression** — §20.28 chat journeys + fo1310 hybrid shim still green.

**Explicitly not v1.2:** Slack clone, Cursor Composer LLM backend, anonymous viewers, cross-tenant joins, bundled non-Ollama local servers, **multiple unrelated workflow profiles in one run**, **cross-user API key sync**.
