# Nimbusware Run Status

Read-only VS Code / Cursor status bar chip for an active Nimbusware run. Polls `GET /v1/runs/{id}` and opens Maker Progress in the browser.

## Requirements

- Nimbusware API running locally or on your network
- A run id from Maker or Admin

## Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `nimbusware.apiBase` | `http://127.0.0.1:8765/v1` | API base URL |
| `nimbusware.activeRunId` | *(empty)* | Run id shown in the status bar |

## Commands

- **Nimbusware: Open Maker Progress** — opens `/v1/maker/app/#/progress?run_id=…` for the active run

## Install from source

```bash
cd extensions/nimbusware-status
npm ci
npm run compile
```

In VS Code or Cursor: **Extensions** → **…** → **Install from Location…** and select this folder.

## Package (VSIX)

```bash
npm run package
```

Install the generated `.vsix` via **Install from VSIX…**.

## Marketplace publish (operator)

See [docs/deploy/vscode-marketplace.md](../../docs/deploy/vscode-marketplace.md).

## Related

- MCP IDE bridge: [docs/ide-bridge.md](../../docs/ide-bridge.md)
