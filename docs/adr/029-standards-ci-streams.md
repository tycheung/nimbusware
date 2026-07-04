# ADR 029: Standards CI streams and verdict modes

## Status

Accepted (2026-07).

## Context

Nimbusware CI (`.github/workflows/ci.yml`) runs ~30 sequential steps in a single `unit` job. Hygiene guards (LOC budget, module size), architecture tests (import graph), lint, security, product SLO gates, and pytest share one flat pipeline. `scripts/ci/fast_gates.py` bundles a overlapping subset but is optional and **not** wired to GitHub Actions; several of its checks never block merge.

Runtime verification uses a separate **enforcement depth** axis (ADR 026) and **autopilot** axis (ADR 014). Neither selects paradigm-specific rule bundles (OOP, FP, NASA JPL Rule of Ten) nor assigns per-check outcomes (warn vs block). External tools (SonarQube, CodeQL) run only ad hoc via critique semgrep/bandit — not as first-class CI streams.

Operators building software with Nimbusware need:

- Clear **streams** they can enable per project without copying checker code into attached repos.
- **Verdict modes** per check: warn, critique gate, or hard merge gate.
- Parity between GitHub CI, local `ci_check`, micro-slice verify, and terminal `enforcement.gate`.

## Decision

### Stream taxonomy

Introduce named **CI streams** orchestrated by `packages/standards/runner.py` and declared in `configs/standards/streams.yaml`:

| Stream | Purpose |
|--------|---------|
| `hygiene` | LOC, module caps, YAML budgets, comment prune |
| `architecture` | Import graph, registry completeness |
| `complexity` | AST / cyclomatic limits on hot paths |
| `lint` | ruff check + format |
| `types` | mypy (layout-aware) |
| `security` | bandit, pip-audit, semgrep |
| `test` | pytest, coverage floors |
| `product` | Nimbusware-only contract gates (OpenAPI TS, SLO, publish) |
| `standards` | Paradigm bundles (OOP, FP, NASA-10, …) |
| `external` | Remote analyzers (SonarQube, CodeQL, Snyk, …) |
| `performance` | N+1, ruff perf |

The Nimbusware monorepo runs **all** streams on merge. Attached workspaces run a **subset** derived from facade manifest + enforcement depth + standards profile.

### Verdict modes

Each check declares a `VerdictMode`:

| Mode | Merge CI | Slice gate | Critique |
|------|----------|------------|----------|
| `skip` | — | — | — |
| `warn` | pass | pass | optional emit |
| `critique` | configurable | fail when unanimous | FAIL |
| `hard_gate` | fail | fail | FAIL |

Defaults live in bundle manifests; operators override per run via `run.standards.updated` metadata.

### Third axis: standards profile

Add a **standards profile** orthogonal to autopilot and enforcement depth:

- Selects active **bundles** and **connectors**.
- Maps enforcement depth → enabled streams (level 0 = none; level 10 = all workspace-applicable streams + facade bundles).
- Persisted via `GET/PUT /v1/runs/{id}/standards` and user defaults in `configs/standards/user_profiles.yaml`.

### CI refactor

- Replace flat `unit` steps with `stream-*` jobs (parallel) + `ci-aggregate`.
- Local: `scripts/ci/run_all_streams.py --profile nimbusware-monorepo`.
- `fast_gates.py` delegates to stream runner.

### Workspace contract

Attached repos contain only `.nimbusware/standards.yaml` (pointer to facade + overrides). Checker implementations remain in the Nimbusware installation.

## Consequences

- ADR 026 enforcement presets gain a `standards_profile_id` reference and stream enablement table; level 10 parity expands to include selected bundles, not just ruff/pytest/bandit.
- New package `packages/standards/`; new config tree `configs/standards/`.
- Feature flag `NIMBUSWARE_STANDARDS_PLATFORM=1` gates API and pipeline wiring.
- MCP gains `nimbusware_standards_run` and `nimbusware_standards_report` (see ADR 030).
- Migration: existing `run_*_ci_gate.py` scripts become stream check adapters; no behavioral change until bundles add new rules.

## Alternatives considered

- **Single extended enforcement slider** — rejected; bundles and external connectors are too numerous for one 0–10 scale.
- **Copy standards CLI into customer repos** — rejected; violates “code stays in Nimbusware” and complicates mart updates.
