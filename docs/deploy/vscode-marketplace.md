# VS Code Marketplace publish (operator runbook)

This runbook covers packaging and publishing the **Nimbusware Run Status** extension (`extensions/nimbusware-status/`). **Do not publish until the publisher account and PAT are configured.**

## Prerequisites

1. Create a [Visual Studio Marketplace publisher](https://marketplace.visualstudio.com/managecreatepublisher) (id: `nimbusware` — must match `publisher` in `package.json`).
2. Create an Azure DevOps PAT with **Marketplace → Manage** scope.
3. Store the PAT as `VSCE_PAT` in GitHub Actions secrets (or export locally for manual publish only).

## Local package (no upload)

```bash
cd extensions/nimbusware-status
npm ci
npm run compile
npm run package
```

Or from repo root:

```bash
poetry run python scripts/publish/publish_vscode_extension.py
```

Install the generated `.vsix` via VS Code / Cursor → **Extensions** → **…** → **Install from VSIX…**.

Contract gate (no upload):

```bash
poetry run python scripts/ci/run_publish_vscode_ci_gate.py
```

## Publish to Marketplace (manual)

1. Bump `version` in `extensions/nimbusware-status/package.json` when releasing.
2. Package and publish:

```bash
export VSCE_PAT=...
poetry run python scripts/publish/publish_vscode_extension.py --publish
```

Or from the extension directory:

```bash
npm run publish:marketplace
# prompts for PAT unless VSCE_PAT is set
```

## GitHub Actions (preferred)

Workflow: [`.github/workflows/publish_vscode_extension.yml`](../../.github/workflows/publish_vscode_extension.yml)

1. Add `VSCE_PAT` in repo secrets.
2. Run **Publish VS Code extension** via `workflow_dispatch`.
3. Leave `publish_marketplace` **false** for VSIX artifact only.
4. Set `publish_marketplace=true` only when ready to release — the workflow fails fast if the token is missing.

## Cursor

Cursor supports VS Code extensions from the Marketplace and from VSIX / folder install. MCP integration remains separate — see [ide-bridge.md](../ide-bridge.md).

## Verified by

- Manifest: `tests/unit/test_vscode_extension_manifest.py`
- Workflow contract: `tests/unit/test_publish_vscode_extension_workflow.py`
- Package smoke: `tests/unit/test_publish_vscode_extension.py`
