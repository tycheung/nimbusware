# Mobile native surface (Phase 8 — deferred)

Nimbusware ships **web-first** via Maker at `/v1/maker/app/`. Native mobile (React Native / Expo) is **deferred** until the web vertical slice gate is green (fo2172 + fo2275 journey E2E).

## Current policy

| Surface | Status | Notes |
|---------|--------|-------|
| Maker web (PWA-capable) | **Shipped** | Primary operator UI for all archetypes |
| React Native / Expo catalog | **Deferred** | fo2300–fo2304 |
| Mobile intent routing | **Partial** | Scope discovery chip “Mobile (web-first)” in Chat |

## When mobile starts

Prerequisites from the v1.5 program:

1. fo2172 + fo2275 Playwright journeys stable on web
2. Stack catalog + `campaign_fullstack` gate green on fixtures
3. Collab disciplines + deploy validate shipped on web (Phases 5–6)

## Operator guidance

Use Maker in the mobile browser for field review. Theater, Plan, and Progress tabs are responsive; dedicated native shells are not required for core workflows.
