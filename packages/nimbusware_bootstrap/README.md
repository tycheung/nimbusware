# nimbusware-bootstrap

Thin PyPI-oriented bootstrap wheel that prints one-command install hints for Nimbusware consumers.

## Install from monorepo

```bash
python -m build packages/nimbusware_bootstrap
pip install packages/nimbusware_bootstrap/dist/nimbusware_bootstrap-*.whl
nimbusware-bootstrap --print-only
```

## Install from PyPI (after publish)

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only
```

The helper prints platform-specific launcher download URLs, curl-based clone install lines, and the in-repo install path when a checkout exists.

```bash
nimbusware-bootstrap --install --install-profile barebones
```

## Publish (operator)

Preflight (build + twine check, no upload):

```bash
poetry run python scripts/publish/publish_bootstrap_release.py
```

TestPyPI or production upload (requires API token in env):

```bash
export TESTPYPI_API_TOKEN=...   # or PYPI_API_TOKEN for production
poetry run python scripts/publish/publish_bootstrap_release.py --testpypi
poetry run python scripts/publish/publish_bootstrap_release.py --pypi
```

GitHub Actions (preferred for production):

1. In GitHub → **Settings → Secrets → Actions**, add `PYPI_API_TOKEN` (PyPI account → API token).
2. Optional: `TESTPYPI_API_TOKEN` for TestPyPI dry runs.
3. Run **Publish bootstrap wheel** workflow (`workflow_dispatch`).
4. Leave `publish_pypi` / `publish_testpypi` **false** for build-only validation.
5. Set `publish_pypi=true` only when the token secret is configured — the workflow fails fast if the token is missing.

Local contract gate: `poetry run python scripts/ci/run_publish_bootstrap_ci_gate.py`.

## Clean VM path

On a machine without a monorepo checkout:

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only
python scripts/install_nimbusware.py --consumer-plan   # when install script is available via clone
```

Or use the printed curl line to clone and run `install_nimbusware.py`.

**Install profiles** (v1.2):

| Profile | Use case |
|---------|----------|
| `recommended` (default) | Ollama install + `llama3.1:8b` + `qwen2.5-coder:14b` pull; sets `NIMBUSWARE_USE_LLM=1` when ready |
| `barebones` | Poetry + optional Postgres only; use `nimbusware-run --quick` or add models later in Models tab |

```bash
# Recommended consumer (GPU demo machine)
curl -fsSL …/install_nimbusware.py | python - --clone … --non-interactive --install-profile recommended

# Barebones consumer (fast VM / CI)
curl -fsSL …/install_nimbusware.py | python - --clone … --non-interactive --skip-postgres --install-profile barebones
```

Equivalent today before `--install-profile` ships: add `--skip-ollama` for barebones LLM posture.
