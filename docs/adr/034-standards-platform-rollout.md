# ADR 034: Standards platform rollout (Jul 2026)

## Status

Accepted (2026-07).

## Context

ADR 029 and ADR 030 defined CI streams, bundles, facades, and mart protocol. Through Jul 2026 the platform shipped incrementally: merge-blocking architecture/complexity gates first, then full parallel stream CI, runtime gate wiring, Maker/Admin UI, and env-gated external connectors.

Planning ledgers (`standards.md`, `efficiency.md`) were merged into `PLAN_GAP.md` and §20.41 of the normative local plan.

## Decision

### Shipped surface

1. **CI:** Nine parallel GitHub Actions jobs (`hygiene` … `performance`) plus `stream-aggregate` over JSON artifacts; local parity via `run_all_streams.py --profile nimbusware-monorepo`.
2. **Runtime:** `run.standards.updated` on `PUT /runs/{id}/standards`; `slice.standards` gate step; standards metadata on terminal `enforcement.gate` when platform enabled.
3. **Profiles:** Facade manifests, bundle execution, `.nimbusware/standards.yaml` overlay write on run update, `/users/me/standards-profile`.
4. **UI:** Maker Standards ribbon (facade, bundles, run-now) and Progress chip; Admin Standards mart install stub.
5. **Connectors:** Semgrep in security stream; SonarQube/CodeQL/Snyk registered with env-gated skip (CLI execution deferred).

### Feature flag

`NIMBUSWARE_STANDARDS_PLATFORM` defaults **on**. Set to `0` to disable standards execution on attached workspaces.

### Remaining (non-blocking)

- Real SonarQube/CodeQL/Snyk CLI scans when credentials present.
- `api-design` and `accessibility` bundles; JVM/Rust agent hygiene.
- Dedupe overlapping checks between stream matrix and flat `unit` job.
- Market track M2–M7 (fullstack e2e default, demo journey, node enforcement bundle).

## Consequences

- Merge CI credibility improved: architecture/complexity and all named streams block before unit tests.
- Attached workspaces inherit rigor via facades without vendoring `packages/standards` into customer repos.
- Further consolidation tracked in `PLAN_GAP.md` Track B/C; normative contract remains ADR 029/030.
