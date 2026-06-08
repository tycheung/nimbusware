# ADR 010: UI controller and browser regression DSL

## Status

Accepted.

## Context

HTTP-only PUT E2E cannot validate SPA interactions (login, click, keyboard nav).

## Decision

1. `UiFlowStep` DSL (`goto`, `click`, `fill`, `press`, `expect_*`).
2. `BrowserController` reuses persistent Playwright page per workspace key.
3. Timeline stages: `dev_env.ui_regression.passed|failed`.

## Consequences

- Playwright required for UI regression routes; skipped gracefully when absent in unit tests.
- UI flows ship with `tiny_web_app` smoke template.
