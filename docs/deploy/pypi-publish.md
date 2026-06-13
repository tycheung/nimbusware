# PyPI publish (operator runbook)

This runbook covers installing Nimbusware wheels from PyPI and publishing the bootstrap package. **Do not publish until tokens and version bumps are reviewed.**

## Install from PyPI (consumer)

After publish, consumers install the thin bootstrap wheel:

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only
```

The helper prints clone/install hints. Full monorepo installs remain via `scripts/install_nimbusware.py` from a checkout.

## Local build (pre-publish validation)

```bash
python -m build packages/nimbusware_bootstrap
pip install packages/nimbusware_bootstrap/dist/nimbusware_bootstrap-*.whl
nimbusware-bootstrap --print-only
```

Contract gate (no upload):

```bash
poetry run python scripts/run_publish_bootstrap_ci_gate.py
```

## Publish with twine (manual)

1. Create a PyPI API token (account → **API tokens**). Store as `PYPI_API_TOKEN` in GitHub Actions secrets for CI, or export locally for manual upload only.
2. Bump version in `packages/nimbusware_bootstrap/pyproject.toml` when releasing.
3. Build artifacts:

```bash
python -m build packages/nimbusware_bootstrap
```

4. Dry-run upload to TestPyPI (optional):

```bash
python -m twine upload --repository testpypi packages/nimbusware_bootstrap/dist/*
```

5. Production upload (operator only — **do not run in CI without approval**):

```bash
python -m twine upload packages/nimbusware_bootstrap/dist/*
```

Use `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<pypi-api-token>` when prompted.

## GitHub Actions (preferred)

Workflow: [`.github/workflows/publish_bootstrap.yml`](../../.github/workflows/publish_bootstrap.yml)

1. Add `PYPI_API_TOKEN` (and optional `TESTPYPI_API_TOKEN`) in repo secrets.
2. Run **Publish bootstrap wheel** via `workflow_dispatch`.
3. Leave `publish_pypi` / `publish_testpypi` **false** for build-only validation.
4. Set `publish_pypi=true` only when ready to release — the workflow fails fast if the token is missing.

See also: [`packages/nimbusware_bootstrap/README.md`](../../packages/nimbusware_bootstrap/README.md).
