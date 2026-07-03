# Fleet Playwright browser pool (production)

PUT E2E and factory cadence can attach to a **remote Chromium** via Playwright WebSocket endpoint instead of launching local browsers on each API/worker pod.

## Configuration

Set on API and worker processes (Helm `secrets` or env):

```bash
NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT=ws://playwright-pool.internal:3000/chromium
```

Probe connectivity:

```python
from orchestrator.fleet.playwright import probe_fleet_playwright_endpoint
probe_fleet_playwright_endpoint()
```

PUT E2E evidence and factory cadence metadata include `fleet_playwright.connected` when the probe succeeds (`fleet_playwright.py`).

## Kubernetes layout

1. Deploy a dedicated Playwright service (browserless, `@playwright/test` docker image, or vendor pool).
2. NetworkPolicy: allow worker pods → pool namespace on the WS port only.
3. Scale pool replicas from concurrent factory tier T3 campaigns (start with 2× peak campaign count).

## Helm reference

See [helm.md](helm.md) for ingress/TLS; fleet Playwright is **external** to the nimbusware chart — document the WS URL in your values overlay:

```yaml
secrets:
  fleetPlaywrightWs: "ws://playwright-pool:3000/chromium"
```

Wire through your deployment template as `NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT`.

## Failure modes

| Symptom | Action |
|---------|--------|
| `connected=false` in evidence | Check pool health, TLS termination on WS, firewall |
| Timeouts on T3 cadence | Increase pool size or `NIMBUSWARE_SLICE_LSP_TIMEOUT_SEC` separately |
| Local fallback | Unset env; PUT E2E uses bundled Chromium on worker node |

## Weekly CI

Repository weekly workflow exercises PUT E2E without fleet pool by default. Add a scheduled job with the env set against a staging pool before promoting pool changes to production.
