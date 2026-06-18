# Playwright button coverage

Nimbusware does **not** aim for 100% per-button Playwright coverage. Coverage is tracked as an **inventory + wiring contract**:

| Artifact | Purpose |
|----------|---------|
| [`playwright_button_inventory.yaml`](playwright_button_inventory.yaml) | Auto-generated list of every `data-testid` on a `<button>` (plus dynamic `dataset.testid` buttons) in Maker/Admin UI |
| [`playwright_button_click_wiring.yaml`](playwright_button_click_wiring.yaml) | Curated buttons that **must** be clicked in CI specs |
| [`test_playwright_button_coverage.py`](test_playwright_button_coverage.py) | Gate: inventory freshness, wiring specs exist, wired buttons call `.click()` |
| [`maker_button_clicks.spec.ts`](../e2e/web/maker_button_clicks.spec.ts) | Click tests for controls that were previously visibility-only |

## Regenerate inventory

```bash
poetry run python scripts/ci/audit_playwright_button_coverage.py --write
poetry run python scripts/ci/audit_playwright_button_coverage.py --check   # CI freshness gate
```

## Current snapshot

After the button-click expansion (see inventory `summary`):

- **~116** inventoried buttons (`data-testid` on buttons)
- **~34** clicked in Playwright specs
- **~7** visible-only (asserted but not clicked)
- **~75** unwired (no Playwright reference yet)

Click ratio floor in CI: **25%** (current inventory: **29%**).

Extended click suites:

- `maker_button_clicks.spec.ts` — compaction, dev-env, interjection, review advanced, integrator refresh
- `maker_playwright_extended.spec.ts` — campaign pause, build submit, wizard, plan/review actions, chat slice escalation
- `admin_button_clicks.spec.ts` — research approve, Ollama pull

## Adding a required click

1. Add or extend a spec under `tests/e2e/web/` with `getByTestId("…").click()` (or role button click).
2. Map the test id in `playwright_button_click_wiring.yaml`.
3. Regenerate inventory (`--write`) and run `poetry run python scripts/ci/run_playwright_button_ci_gate.py`.

## Relationship to parity matrix

[`parity_matrix.yaml`](parity_matrix.yaml) tracks **feature** parity (chat classify, launch scorecard, fleet compare). Button wiring tracks **interaction** parity for operator-critical controls. A feature can be parity-complete while only smoke-visible in Playwright.

See also [`tests/README.md`](../README.md) (Playwright section).
