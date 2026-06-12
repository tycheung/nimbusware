# Security and quality gates

Nimbusware CI treats static analysis and dependency audit as **blocking** gates on every pull request.

## Local parity

```powershell
.\scripts\ci_check.ps1
```

```bash
./scripts/ci_check.sh
```

## Tools

| Tool | Command | Config |
|------|---------|--------|
| **bandit** | `poetry run bandit -c pyproject.toml -r packages` | `[tool.bandit]` in `pyproject.toml` |
| **pip-audit** | `poetry run pip-audit` | Locked `poetry.lock` |
| **ruff** | format + lint on `packages` and `tests` | `[tool.ruff]` |
| **mypy** | tranches via `scripts/mypy_ci_targets.py` | strict islands |
| **Intent→patch SLO** | `scripts/run_intent_to_patch_ci_gate.py` | `benchmarks/latest_intent_to_patch.json` median ≤ 180s |
| **Classifier acceptance SLO** | `scripts/run_classifier_acceptance_ci_gate.py` | `benchmarks/latest_classifier_acceptance.json` rate ≥ 70% |
| **Framework pack** | `scripts/run_framework_pack_ci_gate.py` | launch-test framework YAML smoke |

Failures in bandit or pip-audit block merge the same way as pytest coverage floors.

## Operator surfacing

- **Admin → Metrics** — competitive run analytics snapshot (not a substitute for SOC tooling).
- **Enterprise audit export** — `GET /v1/enterprise/audit-export` bundles IAM, events, and tenant research/egress ledgers.
- **Release** — SBOM artifact on version tags (`.github/workflows/sbom.yml`).

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md).
