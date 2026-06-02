# PLAN_GAP — Full-Repo Maturity Upgrade

Local ledger (gitignored). Tracks baseline, phase objectives, CI evidence, and residual risks.

## Baseline maturity: 7.4 / 10

| Dimension | Score | Notes |
|-----------|-------|-------|
| Architecture | 8.5 | Event sourcing, ADRs, layering guards, facades |
| Quality gates | 7.5 | Strong CI; format check was advisory |
| Testing | 8.0 | Large suite; UI largely omitted from coverage denominator |
| Typing | 6.0 | Strict global config; broad `ignore_errors` on UI + `_pipeline` |
| Security | 7.5 | bandit/pip-audit/egress/IAM; OIDC design-only |
| Documentation | 8.0 | README/ARCHITECTURE/package READMEs; some drift |
| Maintainability | 7.0 | Size/import guards; console/orchestrator complexity |

## Prioritized gaps

1. **High** — Broad mypy ignores: `nimbusware_console.*`, `nimbusware_maker.*`, `hermes_orchestrator._pipeline.*`
2. **High** — CI mypy scope smaller than packages under strict config
3. **Med** — `ruff format --check` non-blocking in CI
4. **Med** — Coverage omit list excludes most Streamlit UI
5. **Low** — Single Python version in CI (3.11)

## Broad ignore inventory (baseline)

| Override | Scope | Rationale (baseline) |
|----------|-------|----------------------|
| `hermes_orchestrator._pipeline.*` | Pipeline mixins | MRO/typing debt; incremental strict islands elsewhere |
| `nimbusware_console.*`, `nimbusware_maker.*` | All UI | Streamlit pages/displays; services re-enabled below |
| Services carve-out | `*.services.*` | Strict islands in CI |
| Tranche B | projections, client, agent_tools | CI-checked |
| API partial | ollama routes/schemas, errors | CI-checked pilot |

## Phase objectives and acceptance

| Phase | Objective | Exit criteria |
|-------|-----------|---------------|
| 0 | Baseline ledger | This file + `ci_check.ps1` green; no commit |
| 1 | CI hardening | Format check blocking; docs synced |
| 2A | Typing round 1 | CI mypy + tranche C core libs; commit |
| 2B | Typing round 2 | Expanded API/orchestrator leaves in CI; narrowed ignores where safe |
| 2C+ | Typing rounds | Broad ignores minimal/justified; commit per round |
| 3 | Coverage confidence | Floors/policy aligned; commit |
| 4 | Security/ops | Hardening + docs; commit |
| 5 | Comments/docs | Repo-wide cleanup + README refresh; commit |

## CI evidence log

| Phase | Date | `ci_check.ps1` | Commit | Notes |
|-------|------|----------------|--------|-------|
| 0 | 2026-06-02 | pass | — | Baseline capture |

## Typing round deltas

| Round | CI mypy targets added | Ignores removed/narrowed | Residual broad ignores |
|-------|----------------------|--------------------------|------------------------|
| baseline | services, tranche B, API pilot | — | UI, `_pipeline` |

## Post-upgrade target rating

Target: **8.2+ / 10** after phases 1–5 (typing ≥7.5, quality gates ≥8.5).
