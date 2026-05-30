# Nimbusware Admin Console

**Admin/dev-only** Streamlit control plane. Not the default product UI — use `nimbusware_maker` for the user loop.

## Entry

- `packages/nimbusware_console/app.py` — load gate + `main.render_main()`
- Launch: `nimbusware-admin`, `nimbusware-run --admin`, or launcher **Admin Console…**

## Layout

| Area | Module |
|------|--------|
| Run list / detail | `pages/run_list.py`, `pages/run_detail/` |
| Config tooling | `pages/config_tooling/` |
| Workflow integrator (fo131–fo140) | `pages/config_tooling/workflows/integrator/` |
| Bundle catalog + FAISS | `pages/config_tooling/bundles/` |
| Enterprise panels | `enterprise_console_ui.py` |
| Operator chat | `operator_chat.py` |

## Refactor status (Lane R)

| Area | Status |
|------|--------|
| `workflows/integrator/` | **Done** — 10 section modules + composer |
| `config_tooling/bundles/` | **Done** — `catalog_search.py` + `faiss_readiness/` (4 modules) |
| `bundle_catalog/catalog_local/` | **Done** — 8 modules (`summary`, `tags`, rollups, `search`, `faiss_helpers`) |
| `components/explainer_panel.py` | **Done** — integrator explainer export panels |
| `components/operator_metrics.py` | **Done** — shared field/value metrics + CSV/JSON export helpers |
| `integrator_gate/`, `integrator_preview/`, `persona_catalog/` | **Done** — split from former god modules (facades kept) |
| `bundle_catalog/faiss_status/` | **Done** — `status`, `readiness`, `index_status`, `drilldown` |
| `pages/config_tooling/_common.py` | **Done** — prune path + session wiring |
| `bundles/_shared.py` | **Done** — re-exports `workflows/_shared.py` |
| HTTP via `nimbusware_client` | **Done** — enforced by `test_console_does_not_import_httpx_directly` |
| `pages/run_detail/` explicit imports | **Done** — no `from _imports import *`; `test_run_detail_sections_do_not_star_import` |

**Rule:** no module >400 lines where feasible.

## Shared imports

Workflow sections use `pages/config_tooling/workflows/_shared.py`. Bundle sections use `pages/config_tooling/bundles/_shared.py`. HTTP calls should use `nimbusware_client.http`.
