# ui_shared

Framework-agnostic JavaScript and CSS shared by **Maker** (Alpine ESM) and **Admin** (Preact/Vite).

## Runtime

Served at `/v1/ui_shared/` when the API mounts `api.routes.ui_shared_web`.

Maker imports: `../../../ui_shared/js/<module>.js` (from `static/js/`)  
Admin imports: `@nimbusware/ui-shared/js/<module>.js` (Vite alias)

## Modules

| Path | Exports |
|------|---------|
| `js/api-core.js` | `parseApiErrorBody`, `fetchJson` |
| `js/formatters.js` | `fmtRate`, `fmtFit`, `formatGateSummary` |
| `js/launch-scorecard.js` | `scorecardFromTimeline`, `renderLaunchScorecard`, `fetchScorecardForRun` |
| `js/theater-dom.js` | `appendTheaterLine` |
| `css/tokens-base.css` | Shared design tokens and utility classes |

## Tests

```bash
cd packages/ui_shared && npm test
```
