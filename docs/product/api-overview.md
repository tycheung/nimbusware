# API overview

All routes are under `/v1`. OpenAPI groups operations as **user** (Maker) or **admin** (Admin Console) at `/docs`.

## Auth

| Route group | Individual | Enterprise |
|-------------|------------|------------|
| **User** (`user` tag) | Open on localhost | `X-Nimbusware-Api-Key` with `maker_user` scope |
| **Admin** (`admin` tag) | `X-Nimbusware-Admin-Token` | `maker_admin` scope or admin token |

## Core endpoints (all editions)

| Area | Endpoints | Access |
|------|-----------|--------|
| **Runs** | `GET/POST /runs`, timeline, findings | User |
| **Maker progress** | `GET /runs/{id}/maker-progress`, SSE stream | User |
| **Theater** | `GET /runs/{id}/theater`, SSE stream, export | User |
| **Chat** | `/chat/sessions`, `/chat/classify`, start/fork/graph | User |
| **Research / stitch** | `/runs/{id}/research`, `/stitch-summary` | User |
| **Maker approval** | pending, plan approve, slice prepare/apply/skip | User |
| **Autopilot** | `GET/PUT /runs/{id}/autopilot` | User |
| **Dev environment** | `GET/POST /runs/{id}/dev-env/*` | User |
| **Platform** | edition, readiness, hardware, analytics | User |
| **Deploy** | `POST /platform/deploy/terraform-validate`, `GET/PUT /platform/deploy/credentials`, `POST /platform/deploy/approve`, workflow template | User |
| **Collab** | `/platform/collab-settings`, `/platform/collab-disciplines`, `GET/PUT /users/me/discipline-profile`, `GET/PUT /users/me/participant-context` | User |
| **Projects** | `GET/POST/PATCH /projects` (User); `DELETE` (Admin) | Mixed |
| **Bundles** | search (User); catalog edit (Admin) | Mixed |
| **Personas** | shelf read (User); CRUD (Admin) | Mixed |
| **Admin BFF** | `/admin/ui/runs/{id}/…` panels | Admin |

## Context & memory APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/runs/{id}/context_budget` | Advisory context budget chip |
| `POST /v1/runs/{id}/compact` | Agent context compaction |
| `POST /v1/runs/{id}/replay-from` | Replay from checkpoint |
| `GET/POST /v1/projects/{id}/context-artifacts` | Context artifact library |

See [reference/context-efficiency.md](../reference/context-efficiency.md) for flags and compaction details.

## Enterprise-only

| Area | Endpoints |
|------|-----------|
| **IAM** | bootstrap, tenants, API keys |
| **Fleet memory** | status, rebuild, search, sync |
| **Fleet worker** | health, metrics |
| **Fleet Ollama SLI** | status, preflight-aggregate |

Full route tables evolve with OpenAPI — regenerate Admin types after API changes (`scripts/ci/run_openapi_ts_ci_gate.py`).
