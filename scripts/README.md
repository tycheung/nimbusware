# Nimbusware scripts

Operator, CI, install, and release helpers. **Public entry points** stay at `scripts/` root (thin wrappers); implementations live in subdirectories below.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`ci/`](ci/) | Local CI parity (`ci_check.ps1` / `.sh`), quality gates, mypy targets, coverage floors, OpenAPI TS gate, integration-like pytest |
| [`install/`](install/) | Universal installer (`install_nimbusware.py`), Ollama/Postgres setup, bootstrap consumer, pilot flows |
| [`database/`](database/) | Postgres schema apply (`apply_event_store`), retention purge, `postgres_schema` helpers |
| [`benchmarks/`](benchmarks/) | Intent-to-patch & classifier metrics, SWE-bench harness, factory weekly CI, launch eval |
| [`faiss/`](faiss/) | Bundle & memory FAISS index build/rebuild |
| [`codegen/`](codegen/) | OpenAPI → TypeScript, model catalog & bundle sync |
| [`ops/`](ops/) | Dispatch worker, campaign/redis/fullstack soaks, e2e smoke, scraper prune, replay |
| [`publish/`](publish/) | Launcher PyInstaller builds, release zips/dmg/tar.gz, bootstrap & VS Code publish |
| [`runbooks/`](runbooks/) | Operator runbooks (fleet dispatch, Redis soak, campaign soak, Ollama SLI) |

## Common entry points

```bash
# Local CI (mirrors .github/workflows/ci.yml unit job)
./scripts/ci_check.ps1          # Windows
./scripts/ci_check.sh           # POSIX

# Install from checkout (curl URL: scripts/install_nimbusware.py)
python scripts/install_nimbusware.py
bash scripts/install-nimbusware.sh

# Postgres schema (K8s/Helm, docker-compose, integration CI)
NIMBUSWARE_DATABASE_URL=postgresql://... ./scripts/apply_event_store.sh
```

## CI gates (`ci/`)

| Script | Role |
|--------|------|
| `run_openapi_ts_ci_gate.py` | Regenerate Admin `schema.d.ts` / snapshot `openapi.json` |
| `run_framework_pack_ci_gate.py` | JS framework pack + launch-test journeys |
| `run_bootstrap_ci_gate.py` | Bootstrap wheel build smoke |
| `run_publish_launcher_ci_gate.py` | Launcher spec + artifact naming |
| `run_publish_bootstrap_ci_gate.py` | Bootstrap wheel build smoke |
| `run_publish_*_ci_gate.py` | Guard other publish workflows |
| `run_intent_to_patch_ci_gate.py` | Benchmark snapshot SLO |
| `run_classifier_acceptance_ci_gate.py` | Classifier acceptance SLO |
| `audit_operator_env.py` | Enforce `NIMBUSWARE_*` catalog coverage |
| `mypy_ci_targets.py` | Shared mypy target list (CI, pre-commit, local) |

## Install (`install/`)

| Script | Role |
|--------|------|
| `install_nimbusware.py` | Clone, Poetry, Postgres, schema, Ollama, edition profiles |
| `ollama_setup.py` | Ollama pull / health |
| `postgres_windows.py` | Windows Postgres install helpers |
| `bootstrap_consumer.py` | Consumer-wheel install path |

## Ops (`ops/`)

| Script | Role |
|--------|------|
| `run_dispatch_worker.py` | Redis fleet worker (K8s/Helm command) |
| `e2e_smoke.py` | Operator smoke (`e2e_smoke.yml`) |
| `run_*_soak*.py` | Weekly slow-test soaks |
| `prune_scraper_artifacts.py` | Scraper artifact retention |

See [`runbooks/`](runbooks/) for fleet dispatch, Redis soak, and campaign soak procedures.
