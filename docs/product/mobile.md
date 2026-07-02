# Mobile native surface (deferred)

Nimbusware ships **web-first** via Maker at `/v1/maker/app/`. Native mobile (React Native / Expo) is **deferred** until the web vertical slice gate is green (fo2172 + fo2275 journey E2E).

## Current policy

| Surface | Status | Notes |
|---------|--------|-------|
| Maker web (PWA-capable) | **Shipped** | Primary operator UI for all archetypes |
| React Native / Expo catalog | **Scaffold** | fo2300 — `configs/stacks/expo.yaml` in catalog (`status: scaffold`); fo2301–fo2304 deferred |
| Mobile intent routing | **Partial** | Scope discovery chip “Mobile (web-first)” in Chat |
| fo2172 live-LLM soak | **Opt-in** | `scripts/ops/run_fo2172_live_journey_soak.py` + `scripts/ci/run_fo2172_live_ci_gate.py` |

## When mobile starts

Prerequisites from the v1.5 program:

1. fo2172 + fo2275 Playwright journeys stable on web — **mocked journeys shipped**; live soak opt-in via `NIMBUSWARE_FO2172_LIVE=1`
2. Stack catalog + `campaign_fullstack` gate green on fixtures
3. Collab disciplines + deploy validate shipped on web (Phases 5–6)

## fo2300 scaffold

`configs/stacks/expo.yaml` registers the `mobile` surface with `frontend_writer` globs. Campaign dispatch, launch packs (fo2301–fo2302), Maker chip wiring (fo2303), and E2E fixtures (fo2304) remain **deferred**.

## Operator guidance

Use Maker in the mobile browser for field review. Theater, Plan, and Progress tabs are responsive; dedicated native shells are not required for core workflows.

**Manager mode:** append `?manager=1` (or `?mobile=1&manager=1`) to the Maker URL for a read-only PWA with Progress, Scope (manifest approval), and Review tabs. Team leads share scope via **Share for manager** in Chat discovery; managers open `#/scope?session_id=<uuid>`.
