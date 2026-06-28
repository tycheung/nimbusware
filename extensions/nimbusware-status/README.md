# Nimbusware Run Status

Read-only VS Code / Cursor extension: status bar run chip, scope manifest card, `@` discipline routing preview, and deploy deep links. Complements MCP ([docs/ide-bridge.md](../../docs/ide-bridge.md)).

## Requirements

- Nimbusware API running locally or on your network
- A run id from Maker or Admin (for status bar and deploy links)

## Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `nimbusware.apiBase` | `http://127.0.0.1:8765/v1` | API base URL |
| `nimbusware.activeRunId` | *(empty)* | Run id shown in the status bar |
| `nimbusware.soloDiscipline` | *(empty)* | Solo hat (`pm`, `frontend`, `backend`, …) when previewing routes without `@` mentions |

## Commands

- **Nimbusware: Open Maker Progress** — opens `/v1/maker/app/#/progress?run_id=…` for the active run
- **Nimbusware: Show Scope Card** — `POST /v1/chat/scope/recommend` from editor selection; human-readable manifest approval card
- **Nimbusware: Preview @ Discipline Routes** — parse `@frontend`, `@qa`, aliases (`@fe`, `@be`); parity with Maker collab routing
- **Nimbusware: Open Deploy Links** — live API/web URLs from run timeline + Maker deploy cockpit

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
