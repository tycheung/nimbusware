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

Implementation:

- `enforcement_profiles.py` — presets, persistence via `run.enforcement.updated`
- `workspace_layout.py` — detect `packages/` vs `src/` layouts, overlay `.nimbusware/enforcement.yaml`
- `workspace_ci_runner.py` — `run_enforcement_bundle`, `run_workspace_ci_parity`
- `enforcement_pipeline.py` — gate wiring, skip policy, milestone bundles, E2E normalization
- API: `GET/PUT /v1/runs/{id}/enforcement`, `GET /v1/enforcement/presets/{level}`, user profiles at run start via `enforcement_profile_id`
- Feature flag: `NIMBUSWARE_ENFORCEMENT_DEPTH=1` enables pipeline wiring for all runs; explicit `PUT /enforcement` or saved profile also activates per-run
- `run.created` emits `enforcement_effective` by work type (patch→4, slice→5, factory→7)
- Maker Progress tab: enforcement depth slider (orthogonal to autopilot trust slider)
- Enterprise fleet enforcement policy: `GET/PUT /v1/enterprise/tenants/{ref}/enforcement-policy`, Admin Fleet page min/max clamp; `configs/enterprise/fleet_enforcement_policies.yaml`
- Terminal `enforcement.gate` stage runs workspace CI parity when `terminal_parity_ci` is set; posts external CI check when GitHub/GitLab is configured

Level 10 is **workspace-applicable parity** — not control-plane-only gates (import graph, OpenAPI TS, Playwright button inventory, intent→patch SLO).

## Consequences

- `micro_slice_verify`, `slice.gate`, and milestone gates consume `EnforcementProfile` when wired.
- Legacy writer/verifier verify (`lifecycle_verify.py`) runs the enforcement bundle when a profile is active.
- Terminal campaign/micro-slice completion may fail when level-10 parity does not pass.
- `parity_contract_steps()` names match runner step ids (`ruff_workspace`, `pytest_coverage`, etc.; `mypy` optional when no config).
- Enterprise fleet policy mirror: `fleet_enforcement_policies.yaml` (`min_enforcement_level`, `max_enforcement_level`).
