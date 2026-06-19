# ADR 026: Enforcement depth slider

## Status

Accepted.

## Context

Autopilot (ADR 014) controls **when the operator is interrupted** — checkpoint stops, theater noise, resolution rounds. It does not define **how strictly** attached workspaces are verified before gates pass. Nimbusware's own CI (`scripts/ci/ci_check.ps1`) is much stricter than default micro-slice verify (scoped ruff, optional tests, env-gated bandit/mypy).

## Decision

Add a second 0–10 axis, **enforcement depth**, orthogonal to autopilot:

| Level | Label | Summary |
|-------|-------|---------|
| 0 | Sketch | No mechanical gates |
| 4 | Mapped tests | Require tests for changed modules |
| 5 | Balanced | Workspace ruff + bandit; default for slice runs |
| 7 | Pre-production | Format check, full security scan, required E2E |
| 10 | Nimbusware parity | Terminal workspace CI contract (layout-aware ruff/format/pytest+coverage/bandit/pip-audit/mypy) |

Implementation (Phases 1–2):

- `enforcement_profiles.py` — presets, persistence via `run.enforcement.updated`
- `workspace_layout.py` — detect `packages/` vs `src/` layouts, overlay `.nimbusware/enforcement.yaml`
- `workspace_ci_runner.py` — `run_enforcement_bundle`, `run_workspace_ci_parity`
- API: `GET/PUT /v1/runs/{id}/enforcement`, `GET /v1/enforcement/presets/{level}`
- Feature flag: `NIMBUSWARE_ENFORCEMENT_DEPTH=1` (catalog default off until pipeline wiring in Phase 3)
- `run.created` emits `enforcement_effective` by work type (patch→4, slice→5, factory→7)

Level 10 is **workspace-applicable parity** — not control-plane-only gates (import graph, OpenAPI TS, Playwright button inventory, intent→patch SLO).

## Consequences

- Phase 3 will wire `micro_slice_verify` and `slice.gate` to `EnforcementProfile`.
- Enterprise fleet policy mirror: `fleet_enforcement_policies.yaml` (`min_enforcement_level`, `max_enforcement_level`).
- UI dual-slider follows in Phase 4.
