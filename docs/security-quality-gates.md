# Security and quality gates

Nimbusware CI treats static analysis and dependency audit as **blocking** gates on every pull request.

## Local parity

```powershell
.\scripts\ci_check.ps1
```

```bash
./scripts/ci/ci_check.sh
```

## Tools

| Tool | Command | Config |
|------|---------|--------|
| **bandit** | `poetry run bandit -c pyproject.toml -r packages` | `[tool.bandit]` in `pyproject.toml` |
| **pip-audit** | `poetry run pip-audit` | Locked `poetry.lock` |
| **ruff** | format + lint on `packages` and `tests` | `[tool.ruff]` |
| **mypy** | tranches via `scripts/ci/mypy_ci_targets.py` | strict islands |
| **Intent→patch SLO** | `scripts/ci/run_intent_to_patch_ci_gate.py` | Live harness (`measure_intent_to_patch.py --runs 1`) + committed snapshot median ≤ 180s on stub fixture |
| **Classifier acceptance SLO** | `scripts/ci/run_classifier_acceptance_ci_gate.py` | Live harness (`measure_classifier_acceptance.py`) + snapshot rate ≥ 70% (rules-first, no LLM) |
| **Framework pack** | `scripts/ci/run_framework_pack_ci_gate.py` | launch-test framework YAML smoke |

Failures in bandit or pip-audit block merge the same way as pytest coverage floors.

**Standards streams (Jul 2026):** Nine parallel CI jobs run hygiene, architecture, complexity, lint, types, security, test, product, and performance via `scripts/ci/run_stream.py`; `stream-aggregate` merges JSON results. Local parity uses `run_all_streams.py --profile nimbusware-monorepo`. Attached workspaces run facade bundles and enforcement-mapped streams during the slice gate (`slice.standards`) when `NIMBUSWARE_STANDARDS_PLATFORM=1` (default). Semgrep, SonarQube, CodeQL, and Snyk connectors are env-gated in the security stream. API: `GET /v1/standards/registry`, `GET/PUT /v1/runs/{id}/standards`, `POST /v1/runs/{id}/standards/run`, `GET/PUT /v1/users/me/standards-profile`. Admin: **Standards mart** at `/v1/admin/app/standards`. See [ADR 029](adr/029-standards-ci-streams.md) and [ADR 030](adr/030-standards-bundles-mart.md).

**Workspace enforcement depth** (attached projects): `workspace_ci_runner.run_enforcement_bundle` applies layout-aware checks at levels 0–10; level 10 runs applicable workspace parity steps and includes standards results in `enforcement.gate` metadata when the standards platform is enabled. Terminal runs emit `enforcement.gate` with optional GitHub/GitLab status when `terminal_parity_ci` is active. API: `GET/PUT /v1/runs/{id}/enforcement`; enterprise tenants: `GET/PUT /v1/enterprise/tenants/{ref}/enforcement-policy`. See [ADR 026](../adr/026-enforcement-depth-slider.md).

## Tiered CI layout (Jul 2026)

| Layer | What runs |
|-------|-----------|
| **streams** (matrix) | Nine standards streams in parallel; `stream-aggregate` merges JSON |
| **unit** | Product gates not yet deduped into streams (coverage floors, bootstrap, SLO gates) + prune/trim docstring gates |
| **web** | Vitest (maker_web, admin_ui) + Playwright |
| **integration / e2e** | Postgres journeys (separate jobs) |

Fast local subset: `poetry run python scripts/ci/fast_gates.py` (architecture + complexity only). Full local parity: `scripts/ci/ci_check.sh` or `ci_check.ps1` (includes `run_all_streams.py --profile nimbusware-monorepo`).

## Operator surfacing

- **Admin → Metrics** — competitive run analytics snapshot (not a substitute for SOC tooling).
- **Enterprise audit export** — `GET /v1/enterprise/audit-export` bundles IAM, events, and tenant research/egress ledgers.
- **Release** — SBOM artifact on version tags (`.github/workflows/sbom.yml`).

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md).
