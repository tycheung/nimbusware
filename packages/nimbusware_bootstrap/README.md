# nimbusware-bootstrap

Thin PyPI-oriented bootstrap wheel that prints one-command install hints for Nimbusware consumers.

From the monorepo root:

```bash
python -m build packages/nimbusware_bootstrap
pip install packages/nimbusware_bootstrap/dist/nimbusware_bootstrap-*.whl
nimbusware-bootstrap --print-only
```

Publish: GitHub Actions `.github/workflows/publish_bootstrap.yml` (`workflow_dispatch`, set `publish_pypi=true` and configure `PYPI_API_TOKEN`).
