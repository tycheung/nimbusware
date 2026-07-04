# Packages

Python libraries and web assets for Nimbusware live under `packages/`. The root [`pyproject.toml`](../pyproject.toml) installs them as top-level import names (`import api`, `import orchestrator`, …) — no `nimbusware_` prefix on package names (`agent_core` is the exception).

**Canonical layering** (data flow, auth, import rules): [ARCHITECTURE.md](../ARCHITECTURE.md). **Directory depth conventions** (domain subpackages, no import shims): [ADR 028](../docs/adr/028-package-directory-depth.md).

```text
UI ──► api ──► orchestrator / projections / iam
              └──► store + config ──► PostgreSQL (or in-memory)
```

Each row below links to a package README when one exists.

---

## Core & contracts

| Package | Responsibility | Notes |
|---------|----------------|-------|
| [`agent_core`](agent_core/) | Shared **domain models** and read helpers: event payloads (`models/`), `stage_graph`, `slice_plan`, `prompt_tiers` (cache-aware assembly), `context_budget`, `tool_output_offload`, `token_telemetry`, critique stage IDs, campaign/critic read parsers (`read/`). | No HTTP or UI. Import boundary for event shapes used by `store`, `orchestrator`, and `projections`. |
| [`store`](store/) | **Append-only event store**: `PostgresEventStore`, `InMemoryEventStore`, migrations under `store/migrations/`. | Source of truth for run timelines. |
| [`config`](config/) | **Versioned configuration** in Postgres + YAML materializer; provider vault, model-routing sections, workflow reads. Canonical routing file: `configs/model-routing.yaml`. | CLI: `nimbusware-config`. |
| [`env`](env/) | **Edition gate**, dotenv, desktop launchers, **~256-key** settings catalog (`settings_catalog*`, `env_flags`, `settings_resolve`). | All `NIMBUSWARE_*` reads should go through helpers here. CLIs: `nimbusware-run`, `nimbusware-admin`, `nimbusware-launcher`. |
| [`client`](client/) | Shared **HTTP client** for Maker/Admin UIs (`httpx`, API key / admin token headers). | Used by frontends and scripts; not for server `services/*` (those call domain code directly). |

---

## Agent runtime

| Package | Responsibility | Notes |
|---------|----------------|-------|
| [`orchestrator`](orchestrator/) | **Run pipeline**: `RunOrchestrator` (`pipeline.py`, `_pipeline/stage_registry.py` mixins), workflow blocks, slice loop, critics, gates, campaign driver, fleet policies, factory/PUT E2E, dev env, routing, replay. | Domain subpackages: `workflow/`, `slice/`, `fleet/`, `critique/`, `campaign/`, `factory/`, `dev_env/`, `routing/`, `integrator/`, `collab/`, `replay/`, `repo_intel/`, `profiles/`, `scraper/`, `stack/`, `llm/`, `launch/`, `escalation/`, `improvement/`, `interaction/`. CLIs: `nimbusware-preflight`, `nimbusware-run-worker`, `nimbusware-memory-replay`, etc. |
| [`agent_tools`](agent_tools/) | **JIT agent loop** for slice implement: tool registry, allowlist, dual `ToolResult` output, filesystem jail, sandbox backends, risk caps. | Invoked from orchestrator slice stages. |
| [`executor`](executor/) | **Role-gated outbound HTTP** allowlists for scraper and agent egress. | See [agent-sandbox.md](../docs/deploy/agent-sandbox.md). |
| [`extensions`](extensions/) | **Personas**, bundle memory, escalation helpers, custom agents catalog integration. | Must not import `orchestrator` at module level. |
| [`research`](research/) | **Research briefs**, stitch transplant stages, catalog candidates, outcome stats. | Feeds bundle catalog promotion. |
| [`memory`](memory/) | **Repo-scoped retrieval index** (chunk store, embeddings, FAISS, fleet sync). Subpackages: `store/`, `index/`, `fleet/`. | CLIs: `nimbusware-memory-index`, `nimbusware-memory-sync`. |
| [`compute`](compute/) | **Distributed compute mesh**: node registry, work-unit queue, worker policy. | CLI: `nimbusware-compute-worker`. See [compute-mesh.md](../docs/compute-mesh.md). |

---

## API & read models

| Package | Responsibility | Notes |
|---------|----------------|-------|
| [`api`](api/) | **FastAPI control plane** at `/v1`: routes (`routes/`, `routes/runs/`, `routes/enterprise/`), schemas, deps, OpenAPI. | CLI: `nimbusware-api`. Must not be imported by `orchestrator`. |
| [`projections`](projections/) | **Event → read models**: `builders/` (timeline, theater, maker-progress, context budget, …), `fields/` (display order), `exporters/`. | API and `console` consume builders; no HTTP in builders. |
| [`iam`](iam/) | **Enterprise IAM**: tenants, API keys, action log for audit export. | Middleware + `iam/store.py`. |
| [`auth`](auth/) | **Collaborative-chat auth** (register/login, session tokens) when `NIMBUSWARE_COLLAB_ENABLED=1`. | Individual edition loopback; Enterprise uses IAM keys. |
| [`mcp`](mcp/) | **Stdio MCP IDE bridge** — classify, patch, interject, chat graph/fork, run status, theater. | CLI: `nimbusware-mcp`. [ide-bridge.md](../docs/ide-bridge.md). |

---

## Maker & operator surfaces

| Package | Responsibility | Notes |
|---------|----------------|-------|
| [`maker`](maker/) | **Maker server logic**: chat sessions, intent classifier, readiness, workspace snapshots, deploy pipeline, collab policy, slice workflow approval. Subpackages: `chat/`, `intent/`, `readiness/`, `workspace/`, `deploy/`, `collab/`, `services/`, `slice_workflow/`. | CLI: `nimbusware-maker`. |
| [`maker_web`](maker_web/) | **Maker web app** (Alpine.js): tabs, SSE progress, session hub, operator ribbons. Served at `/v1/maker/app/`. | Static assets under `static/`. |
| [`console`](console/) | **Admin display layer** + BFF helpers: workflow explainers (`workflow_explainers/`, `explainer_core/`), bundle catalog, integrator gate panels, fleet formatters. | Python only; pairs with `admin_ui` SPA. HTTP via `console/services/*`. |
| [`admin_ui`](admin_ui/) | **Admin SPA** (Preact/Vite): fleet, metrics, hardware, compliance. Served at `/v1/admin/app/`. | Build: `cd packages/admin_ui && npm run build`. |
| [`ui_shared`](ui_shared/) | **Shared JS/CSS** for Maker and Admin (`api-core`, formatters, launch scorecard, theater DOM, `chat-intent-hints`, tokens). | Served at `/v1/ui_shared/`. Display YAML specs: `configs/displays/`. |

---

## Platform & hardware

| Package | Responsibility | Notes |
|---------|----------------|-------|
| [`hw`](hw/) | **Hardware probe**, governor, pressure sampling, catalog fit; local and SSH remote fleet probe. | Routes: `/v1/platform/hardware*`. |
| [`bootstrap`](bootstrap/) | **Thin install bootstrap** wheel (`nimbusware-bootstrap` on PyPI) — launcher hints only. | Separate `pyproject.toml`; not part of main Poetry package list. |

---

## Import rules (summary)

Enforced by [`tests/unit/test_import_graph.py`](../tests/unit/test_import_graph.py):

- `orchestrator` must not import `api` at module level (use `projections`).
- `extensions` must not import `orchestrator` at module level.
- `projections` must not import `orchestrator` at module level.
- Web UIs use `/v1` via `fetch` or `client`; Python display code uses `console/services/*`, not ad-hoc `httpx`.

---

## Per-package documentation

| Package | README |
|---------|--------|
| agent_core | [agent_core/README.md](agent_core/README.md) |
| agent_tools | [agent_tools/README.md](agent_tools/README.md) |
| admin_ui | [admin_ui/README.md](admin_ui/README.md) |
| api | [api/README.md](api/README.md) |
| bootstrap | [bootstrap/README.md](bootstrap/README.md) |
| client | [client/README.md](client/README.md) |
| config | [config/README.md](config/README.md) |
| console | [console/README.md](console/README.md) |
| env | [env/README.md](env/README.md) |
| executor | [executor/README.md](executor/README.md) |
| extensions | [extensions/README.md](extensions/README.md) |
| hw | [hw/README.md](hw/README.md) |
| iam | [iam/README.md](iam/README.md) |
| maker | [maker/README.md](maker/README.md) |
| maker_web | [maker_web/README.md](maker_web/README.md) |
| mcp | [mcp/README.md](mcp/README.md) |
| memory | [memory/README.md](memory/README.md) |
| orchestrator | [orchestrator/README.md](orchestrator/README.md) |
| projections | [projections/README.md](projections/README.md) |
| research | [research/README.md](research/README.md) |
| store | [store/README.md](store/README.md) |
| ui_shared | [ui_shared/README.md](ui_shared/README.md) |
| auth | [auth/README.md](auth/README.md) |
| compute | [compute/README.md](compute/README.md) |

---

## Tests mirror packages

Themed test trees avoid shadowing production import names (e.g. no `tests/orchestrator/` — use `tests/orchestrator_pipeline/`). Layout: [tests/README.md](../tests/README.md).
