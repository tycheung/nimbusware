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

**Standards streams (Jul 2026):** Architecture and complexity checks run via `packages/standards` and block merge in the `stream-guardrails` CI job (`scripts/ci/run_all_streams.py --profile nimbusware-core`). Full monorepo profile (`nimbusware-monorepo`) adds hygiene, lint, types, security, test, product, and performance streams. Attached workspaces run facade bundles during `micro_slice.verify` when `NIMBUSWARE_STANDARDS_PLATFORM=1` (default). API: `GET /v1/standards/registry`, `GET/PUT /v1/runs/{id}/standards`, `POST /v1/runs/{id}/standards/run`. See [ADR 029](adr/029-standards-ci-streams.md) and [ADR 030](adr/030-standards-bundles-mart.md).

**Workspace enforcement depth** (attached projects): `workspace_ci_runner.run_enforcement_bundle` applies layout-aware checks at levels 0–10; level 10 runs applicable workspace parity steps (lint, types, security, tests — not the full monorepo stream set). Terminal runs emit `enforcement.gate` with optional GitHub/GitLab status when `terminal_parity_ci` is active. API: `GET/PUT /v1/runs/{id}/enforcement`; enterprise tenants: `GET/PUT /v1/enterprise/tenants/{ref}/enforcement-policy`. See [ADR 026](../adr/026-enforcement-depth-slider.md).

## Operator surfacing

- **Admin → Metrics** — competitive run analytics snapshot (not a substitute for SOC tooling).
- **Enterprise audit export** — `GET /v1/enterprise/audit-export` bundles IAM, events, and tenant research/egress ledgers.
- **Release** — SBOM artifact on version tags (`.github/workflows/sbom.yml`).

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md).
