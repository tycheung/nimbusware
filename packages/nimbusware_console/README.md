# Nimbusware Admin Console

Streamlit **admin/dev control plane** for inspecting runs, editing repo config, and driving operator workflows. This is not the default product UI — end users should use [`nimbusware_maker`](../nimbusware_maker/README.md).

## Running

| Entry | Path / command |
|-------|----------------|
| Streamlit app | `packages/nimbusware_console/app.py` |
| Page composer | `main.render_main()` |
| CLI | `nimbusware-admin`, `nimbusware-run --admin`, or launcher **Admin Console…** |

`app.py` loads dotenv, applies the admin session gate (`admin_gate.require_admin_session`), then calls `render_main()`.

### Environment

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_REPO_ROOT` | Frozen repo root for local YAML reads (catalog, personas, workflows) |
| `NIMBUSWARE_API_BASE` / client defaults | API base for run list, detail, timeline, findings |
| `NIMBUSWARE_MAKER_URL` | Link from run detail → Maker review |
| Admin gate env | See `admin_gate.py` (required before any panel renders) |

Repo root and API base helpers live in `settings.py` (`repo_root()`, `API_BASE`).

## Main UI flow

`main.render_main()` renders, in order:

1. **Sidebar** — custom agents + enterprise fleet toggle
2. **Operator chat** — `operator_chat.py`
3. **Enterprise dashboard** — when fleet mode is active (`enterprise_console_ui.py`)
4. **Run list** — `pages/run_list.py` (pagination, filters, CSV export)
5. **Run detail** — `pages/run_detail/` (summary, timeline, findings, actions)
6. **Config tooling** — `pages/config_tooling/` (bundles + workflows)
7. **Preflight fleet** — `pages/preflight_fleet.py`

Run list session state and query-param sync are centralized in `pages/_state.py` (facade over `_state_keys.py`, `_state_run_list_qp.py`, `_state_run_list_render.py`).

## Directory layout

```
nimbusware_console/
├── app.py, main.py          # entry + section composer
├── settings.py              # API_BASE, repo_root()
├── admin_gate.py            # session gate
├── components/              # shared UI helpers (see below)
├── pages/                   # Streamlit sections
│   ├── run_list.py
│   ├── run_detail/          # per-run panels + timeline sections
│   ├── config_tooling/      # bundles + workflows tooling
│   ├── _state*.py           # run-list session / query-param state
│   └── preflight_fleet.py
├── *\_display.py            # read-only caption/table/export helpers (top-level)
├── *_workflow_explainer/    # workflow YAML explainers (packages + 1-line facades)
├── bundle_catalog/          # local catalog + FAISS status helpers
├── integrator_gate/         # gate summary, history, latest/delta metrics
├── integrator_preview/      # full-workflow merge diff + preview
├── persona_catalog/         # shelves + critique pairings
├── run_escalated/           # escalation timeline display helpers
├── security_scan_on_verify/ # verifier scan timeline display
├── self_refinement/         # self-refinement timeline display
└── …                        # other domain-specific display modules
```

### Pages

| Area | Module | Role |
|------|--------|------|
| Run list | `pages/run_list.py` | Paginated run table, filters, exports |
| Run detail | `pages/run_detail/` | Summary, timeline, findings, critic matrix, actions |
| Config — bundles | `pages/config_tooling/bundles/` | Local catalog search, rollups, FAISS readiness |
| Config — workflows | `pages/config_tooling/workflows/` | Bundle/persona editors, integrator (fo131–fo140), prune |
| Integrator sections | `workflows/integrator/` | Preview, apply, per-knob explainers (10 section modules) |

**Run detail timeline** is split into focused renderers:

| Module | Panels |
|--------|--------|
| `timeline_core.py` | Base timeline fetch |
| `timeline_integrator/` | Integrator gate latest, history, delta |
| `timeline_personas/` | Persona assignment, agent evaluator, self-refinement |
| `timeline_escalation/` | Marker history, run escalated, history, delta |
| `timeline_misc*.py` | Security scan, preflight, scraper, universal critique |

**Config tooling shared imports:**

- Workflows: `pages/config_tooling/workflows/_shared.py` → `_shared_{session,catalog,displays,explainers,integrator}.py`
- Bundles: `pages/config_tooling/bundles/_shared.py` (re-exports workflow shared)

### Display helpers (`*_display.py` and packages)

Top-level `*_display.py` files (and their subpackages) hold **read-only** logic: captions, table rows, operator metrics, JSON/CSV export. Streamlit sections import these; they do not call `st` directly except through page modules.

Common packages (facade `.py` re-exports the package):

| Package | Purpose |
|---------|---------|
| `preflight_cross_run_display/` | Cross-run preflight trend + operator metrics |
| `prune_status_display/` | Scraper artifact prune status |
| `run_list_pagination_display/` | List pagination captions + run-detail summary exports |
| `agent_evaluator_display/` | Agent evaluator timeline captions + metrics |
| `universal_critique_timeline_display/` | Universal critique timeline rows + metrics |
| `integrator_gate/latest_delta/` | Latest vs delta gate metrics |
| `integrator_preview/merge/` | Full-workflow shallow merge diff |
| `persona_catalog/summary/` | Persona catalog operator summary |
| `bundle_catalog/catalog_local/search/` | Bundle search captions + local catalog |
| `bundle_catalog/faiss_status/drilldown/` | FAISS index drilldown tables |

Workflow YAML explainers (all package + 1-line facade):

`integrator_threshold_explainer`, `security_scan_metadata_workflow_explainer`, `agent_evaluator_workflow_explainer`, `escalation_suppress_workflow_explainer`, `self_refinement_workflow_explainer`, `universal_critique_workflow_explainer`.

Disk reads for explainers go through `explainer_workflow_disk.py` and `nimbusware_config.workflow_read` (not raw orchestrator imports).

### Shared components

| Module | Role |
|--------|------|
| `components/operator_metrics.py` | Field/value metrics tables, CSV/JSON export helpers |
| `components/workflow_explainer_helpers.py` | Path, YAML fragment, mtime helpers for explainers |
| `components/explainer_panel.py` | Integrator explainer export panels |
| `components/ui_errors.py` | `render_api_error()` for Streamlit HTTP failures |

## Conventions

### Module size (≤400 lines)

Every `.py` file under this package must stay **≤400 lines**. Enforcement: `tests/unit/test_console_module_size.py` (allowlist is empty — any new file over the limit fails CI).

Prefer **packages with thin facades** over growing monoliths:

```python
# integrator_threshold_explainer.py
from nimbusware_console.integrator_threshold_explainer import *  # noqa: F403
```

Split scripts for reproducibility live under `scripts/split_*.py` (and `scripts/_archive/lane_r/` for one-off migration scripts).

### HTTP and boundaries

- **HTTP:** use `nimbusware_client.http` only — no direct `httpx` imports (`test_console_does_not_import_httpx_directly`).
- **Run projections:** list/detail summaries come from `nimbusware_projections` (API routes import projections; orchestrator keeps shims).
- **Workflow YAML reads:** use `nimbusware_config.workflow_read` from explainers and config tooling.
- **Maker boundary:** orchestrator imports from console packages are limited; maker uses `nimbusware_maker.slice_engine` as the sole orchestrator touchpoint.

### Run detail imports

Run-detail section modules use **explicit imports** from `_imports_display_a/`, `_imports_display_b.py`, and `_imports_common.py` — not `from _imports import *` (`test_run_detail_sections_do_not_star_import`).

`_imports_display_a/` is split into `agent_through_escalation.py` and `findings_through_persona.py` with a re-export facade.

## Tests

| Suite | Location | Covers |
|-------|----------|--------|
| Console integration | `tests/console/test_console_*.py` | Facade exports, major panels, explainers |
| Display unit tests | `tests/unit/test_*_display.py`, `test_*_explainer.py` | Captions, metrics, CSV/JSON export |
| Import graph | `tests/unit/test_import_graph.py` | httpx ban, run-detail import style, projection/workflow_read facades |
| Module size | `tests/unit/test_console_module_size.py` | 400-line guard |

Run console-focused tests:

```bash
poetry run pytest tests/console tests/unit/test_console_module_size.py tests/unit/test_import_graph.py -q
```

## Related packages

| Package | Relationship |
|---------|--------------|
| [`nimbusware_client`](../nimbusware_client/README.md) | HTTP client for all API calls |
| [`nimbusware_api`](../nimbusware_api/README.md) | REST API consumed by run list/detail |
| [`nimbusware_projections`](../nimbusware_projections/run_summary.py) | Run summary projections (`build_run_summary`, list filters) |
| [`nimbusware_config`](../nimbusware_config/workflow_read.py) | Workflow YAML read facade for explainers |
| [`nimbusware_maker`](../nimbusware_maker/README.md) | Default product UI / review loop |
| [`nimbusware_env`](../nimbusware_env/README.md) | Dotenv + feature flags |
