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

The helper prints a curl-based clone install and documents the in-repo path when a checkout exists.

## Publish (operator)

1. In GitHub → **Settings → Secrets → Actions**, add `PYPI_API_TOKEN` (PyPI account → API token).
2. Optional: `TESTPYPI_API_TOKEN` for TestPyPI dry runs.
3. Run **Publish bootstrap wheel** workflow (`workflow_dispatch`).
4. Leave `publish_pypi` / `publish_testpypi` **false** for build-only validation.
5. Set `publish_pypi=true` only when the token secret is configured — the workflow fails fast if the token is missing.

Local contract gate: `poetry run python scripts/run_publish_bootstrap_ci_gate.py`.

## Clean VM path

On a machine without a monorepo checkout:

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only
python scripts/install_nimbusware.py --consumer-plan   # when install script is available via clone
```

Or use the printed curl line to clone and run `install_nimbusware.py --non-interactive --skip-postgres`.
