# ADR 030: Standards bundles, facades, and mart

## Status

Accepted (2026-07).

## Context

ADR 029 defines CI **streams** and **verdict modes**. Operators also need **reusable rule packages** (object-oriented principles, functional programming constraints, NASA JPL Rule of Ten, performance heuristics) and **stack-specific facades** (Python FastAPI, TypeScript React) without vendoring Python into every new repository.

Forks and enterprise tenants will want to publish custom bundles (“financial audit”, “HIPAA logging”) in a discoverable **mart** similar to workflow profiles and custom agents.

## Decision

### Bundle manifests

Each bundle is a versioned YAML file under `configs/standards/bundles/<slug>.yaml`:

- `id`, `display_name`, `description`, `tags`, `origin` (`core` | `curated` | `community` | `enterprise`)
- `checks[]` with `id`, `runner` (import path), `default_verdict`, `params`

Runner code lives in `packages/standards/bundles/`. Bundles compose checks from:

- Existing CI gates (wrapped)
- AST visitors
- Ruff / semgrep rule profiles
- Connector outputs (normalized to `CheckResult`)

Initial core bundles: `nimbusware-core`, `object-oriented`, `functional`, `nasa-jpl-ten`, `solid`, `performance-n-plus-one`, `immutability`, `error-handling`.

### Facade manifests

Facades under `configs/standards/facades/` describe a **target stack**:

- Enabled streams and default verdict overrides
- Default bundle list
- Optional connector slots (credentials via vault / env)

New projects select a facade at run start. Nimbusware writes `.nimbusware/standards.yaml` in the attached workspace containing **references only**.

Export: `nimbusware-standards export-github-workflow --facade <id>` emits a workflow that invokes Nimbusware API or a pinned container — no rule code in customer repo.

### Standards mart

`configs/standards/registry.yaml` indexes bundles, facades, and connectors:

| Tier | Publisher | UI badge | Default verdict cap |
|------|-----------|----------|---------------------|
| `core` | Nimbusware | Core | hard_gate allowed |
| `curated` | Verified fork PR | Curated | hard_gate allowed |
| `community` | Any fork | Community | warn/critique default |
| `enterprise` | Tenant private | Enterprise | fleet policy |

Admin **Standards Mart** page: browse, install to tenant, publish curated entries. Fleet policy (`GET/PUT /v1/enterprise/tenants/{ref}/standards-policy`) mirrors enforcement fleet min/max.

### Fork contribution protocol

1. Add bundle YAML + `packages/standards/bundles/<module>.py` + tests.
2. Register in `registry.yaml` with `origin: community`.
3. Open PR to upstream for `curated` promotion.

Third parties must not copy `packages/standards/` into application repos; only manifest pointers.

### External connectors

Connectors declared in `configs/standards/connectors/<id>.yaml` with `requires.env`, `requires.binaries`, `stream: external`, and `default_verdict`.

Initial targets: SonarQube/SonarCloud, Semgrep (promote from critique), CodeQL, Snyk, Trivy. Connectors implement `packages/standards/connectors/base.py` (`scan()`, `poll_quality_gate()`).

Operator configures per-connector verdict in Maker **Settings → Standards** alongside bundle checks.

### UI

- Maker Settings: facade picker, bundle multi-select, verdict grid, connector credentials.
- Progress tab: standards status chip (parallel to enforcement ribbon).
- Admin Fleet: tenant standards policy.
- Admin Mart: browse/install/publish.

## Consequences

- Depends on ADR 029 stream runner and API routes.
- `workspace_ci_runner.run_enforcement_bundle` delegates paradigm checks to `standards.runner`.
- Community bundles require explicit operator opt-in; fleet can block `origin: community`.
- Documentation: `standards.md` (local design ledger) tracks implementation phases; this ADR is the normative contract for forks.

## Alternatives considered

- **Semgrep-only for all paradigms** — insufficient for NASA-10 / OOP cohesion without custom rules; semgrep remains one tool inside bundles.
- **Git submodule of standards in customer repo** — rejected; update friction and fork drift.
