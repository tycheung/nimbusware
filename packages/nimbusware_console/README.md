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
| `pages/config_tooling/workflows/_shared.py` | **Done** — thin facade over `_shared_{session,catalog,displays,explainers,integrator}.py` |
| `components/ui_errors.py` | **Done** — shared `render_api_error()` for Streamlit HTTP failures |
| `bundles/_shared.py` | **Done** — re-exports `workflows/_shared.py` |
| HTTP via `nimbusware_client` | **Done** — enforced by `test_console_does_not_import_httpx_directly` |
| `pages/run_detail/` explicit imports | **Done** — no `from _imports import *`; `test_run_detail_sections_do_not_star_import` |

**Rule:** no module >400 lines where feasible.

## Refactor status (Lane X — console decomposition)

| Step | Status |
|------|--------|
| X-A `_shared.py` split | **Done** — `_shared_{session,catalog,displays,explainers,integrator}.py` |
| X-B integrator metrics panels | **Done** — `components/workflow_explainer_helpers.py` + 6 integrator sections |
| X-C `run_escalated` CSV/JSON | **Done** — `rows.py` + `metrics.py` use `operator_metrics` |
| X-D `pages/_state.py` | **Done** — `_state_keys.py` + `_state_run_list.py` facade |
| X-E large displays | **Done** — `security_scan_on_verify/` + `self_refinement/` packages (facades kept) |
| X-F API error UI | **Done** — `components/ui_errors.py` |

## Refactor status (Lane Y — projections purity & UI boundary)

| Step | Status |
|------|--------|
| Y-A `build_run_summary` in projections | **Done** — `nimbusware_projections/run_summary.py`; API list/detail import projections; orchestrator shim kept |
| Y-B workflow read facade | **Done** — `nimbusware_config/workflow_read.py`; explainers + `explainer_workflow_disk` use facade; shared path/YAML helpers in `workflow_explainer_helpers` |
| Y-C Maker `slice_workflow` boundary | **Done** — `slice_engine.py` sole orchestrator import site; `packages/nimbusware_maker/README.md` |

## Refactor status (Lane Z — housekeeping)

| Step | Status |
|------|--------|
| Z-A Lane R script archive | **Done** — `scripts/_archive/lane_r/` |
| Z-B package README stubs | **Done** — `nimbusware_{maker,client,api,env}/README.md` |
| Z-C orchestrator module splits | **Done** — `optional_stages_*` + `critique_gates_*` mixin packages (~170–276 LOC each) |

## Optional console decomposition (post-Lane Z)

| Step | Status |
|------|--------|
| Workflow explainer packages | **Done** — 6 explainers split into subpackages with 1-line facades (`integrator_threshold`, `security_scan_metadata`, `agent_evaluator`, `escalation_suppress`, `self_refinement`, `universal_critique`) |
| `pages/_state_run_list.py` | **Done** — `_state_run_list_qp.py` + `_state_run_list_render.py` facade |
| `security_scan` metrics CSV | **Done** — uses `field_value_table_rows_csv` |
| Display packages (batch 2) | **Done** — `preflight_cross_run_display/`, `prune_status_display/`, `run_list_pagination_display/`, `agent_evaluator_display/`; `integrator_gate/latest_delta/`, `integrator_preview/merge/`, `persona_catalog/summary/` |
| Display packages (batch 3) | **Done** — catalog search/FAISS drilldown/universal-critique timeline; run-detail timeline sections; config tooling page panels; `_imports_display_a/` |

**400-line guard:** allowlist is empty — all console modules are ≤400 lines (`tests/unit/test_console_module_size.py`).

## Shared imports

Workflow sections use `pages/config_tooling/workflows/_shared.py`. Bundle sections use `pages/config_tooling/bundles/_shared.py`. HTTP calls should use `nimbusware_client.http`.
