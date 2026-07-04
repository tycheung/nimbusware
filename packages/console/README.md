# Nimbusware Admin Console (backend)

Python admin/dev control plane for inspecting runs, editing repo config, and driving operator workflows. Browser UI: [`admin_ui`](../admin_ui/) at `/v1/admin/app/`. End users: [`maker`](../maker/README.md) at `/v1/maker/app/`.

## Running

| Entry | Command |
|-------|---------|
| Admin web UI | `nimbusware-admin` or `nimbusware-run --admin` |
| API only | `poetry run nimbusware-api` then open `http://127.0.0.1:8000/v1/admin/app/` |

Build Admin SPA before packaging: `cd packages/admin_ui && npm ci && npm run build`.

## Import policy (display modules)

Prefer **package-first** imports for console display code:

| Prefer | Avoid |
|--------|-------|
| `from console.run_escalated import metrics` | Reaching through `run_escalated_display.py` shims from other packages |
| `from console.workflow_explainers.security_critique import payload` | Duplicating explainer field maps in ad-hoc formatters |
| `from projections.builders import …` for read-model fields | Re-parsing raw event payloads in console when a projection exists |

Thin `*_display.py` facades exist only for Admin tab entry points and CI sync (`sync_display_facade.py`). New display logic belongs in the co-located package directory, not in facade barrels.

### Environment

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_REPO_ROOT` | Frozen repo root for local YAML reads |
| `NIMBUSWARE_API_BASE` | API base for run list, detail, timeline |
| `NIMBUSWARE_ADMIN_TOKEN` | Admin gate (`X-Nimbusware-Admin-Token`) |
| `NIMBUSWARE_UI_BACKEND` | `web` (default; pywebview opens `/v1/admin/app/`) |

## Layout

```
console/
├── services/                 # HTTP clients to /v1 (runs, chat, config, ollama, …)
├── components/               # Shared explainer panel + operator metrics helpers
├── explainer_core/           # metrics_scaffold, operator_metrics_exports, schema_metrics, table_rows_csv
├── integrator_core/          # Shared thresholds / min-score / gate emission SSOT (C62)
├── workflow_explainers/      # Unified per-workflow operator explainers (7 slugs)
├── *_display.py              # Thin facades → sibling packages (see sync_display_facade.py)
├── *_display/                # Package-only display modules (no duplicate .py shim)
├── operator_chat_core.py     # Operator chat command handling
├── admin_gate.py             # Token gate helpers
├── integrator_gate/          # Integrator gate latest delta + history
├── integrator_preview/       # Merge diff exports via workflow_exports + sequence_export_json (C41)
├── bundle_catalog/           # Local catalog search, FAISS status, tags rollup
├── persona_catalog/          # Persona pairings, summary metrics, export
├── run_escalated/            # Escalation metrics (YAML: configs/displays/run_escalated_*.yaml)
├── security_scan_on_verify/  # Security scan timeline + linter alignment
├── self_refinement/          # Self-refinement marker history
└── enterprise_console*.py    # Enterprise fleet formatters (Admin Fleet tab)
```

## Display modules (facade entry points)

### Flat `*_display.py` barrels (C64 audit)

| Module | Kind | Action |
|--------|------|--------|
| `integrator_gate_display.py` | Pure facade → `integrator_gate/` | **Keep** — CI-synced |
| `run_escalated_display.py` | Pure facade → `run_escalated/` | **Keep** — CI-synced |
| `self_refinement_display.py` | Pure facade → `self_refinement/` | **Keep** — CI-synced |
| `security_scan_on_verify_display.py` | Pure facade → `security_scan_on_verify/` | **Keep** — CI-synced |
| `findings_display.py` | Local implementation | **Keep** — migrate to package when >400 LOC |
| `critic_matrix_display.py` | Local implementation | **Keep** |
| `critic_reliability_display.py` | Hybrid facade + formatters | **Keep** |
| `preflight_history_display.py` | Local implementation | **Keep** |
| `scraper_fetch_display.py` | Local implementation | **Keep** |
| `bundle_memory_display.py` | Local implementation | **Keep** |
| `memory_display.py` | Hybrid re-export + helpers | **Keep** |
| `persona_assignment_display.py` | Local implementation | **Keep** |
| `implementation_critique_display.py` | Local implementation | **Keep** |
| `micro_slice_packet_display.py` | Local implementation | **Keep** |

Pure facades are regenerated via `scripts/ci/sync_display_facade.py`. Do not collapse into a mega-barrel — each maps to one admin tab.

### Admin surface map

| Module | Admin surface |
|--------|---------------|
| `findings_display.py` | Run findings panel |
| `critic_matrix_display.py` | Live critic matrix |
| `critic_reliability_display.py` | Critic reliability drilldown |
| `integrator_gate_display.py` | Integrator gate status |
| `run_list_pagination_display` | Run list + timeline captions (package) |
| `run_escalated_display.py` | Escalation history facade → `run_escalated/` |
| `preflight_history_display.py` | Preflight cross-run history |
| `preflight_cross_run_display` | Preflight trend metrics (package) |
| `memory_display.py` | Memory influence table |
| `bundle_memory_display.py` | Bundle-scoped memory |
| `prune_status_display` | Memory prune inventory (package) |
| `scraper_fetch_display.py` | Scraper stage artifacts |
| `micro_slice_packet_display.py` | Slice context packet |
| `agent_evaluator_display` | Agent evaluator workflow (package) |
| `universal_critique_timeline_display` | Universal critique timeline (package) |
| `self_refinement_display.py` | Self-refinement markers |
| `security_scan_on_verify_display.py` | Security scan on verify |
| `implementation_critique_display.py` | Phase-3 critique panels |
| `persona_assignment_display.py` | Persona assignment summary |

Nested packages (`bundle_catalog/`, `persona_catalog/`, `integrator_*`, `workflow_explainers/*`) may co-locate related logic in cohesive modules (≤1000 lines per file). Regenerate thin `*_display.py` facades after changing package exports when using shims: `poetry run python scripts/ci/sync_display_facade.py`. Package-only modules (no sibling `.py` shim) are imported by their package name directly.

## Operator metrics scaffold

Console display modules expose operator metrics (table rows, captions, JSON/CSV export) through `explainer_core.operator_metrics_exports`:

| Pattern | Use when |
|---------|----------|
| `install_operator_metrics_module` | Full bundle: metrics + table rows + caption + exports |
| `build_metrics_fn` + `table_rows_fn` | Mapping payloads with declarative field specs |
| `install_named_operator_metrics_exports` | Exports only (custom metrics builders or guard-wrapped JSON) |

Reference: `agent_evaluator_display/metrics.py`. Prefer `agent_core.coercion` guards over hand-rolled `isinstance` checks. Custom run-id export slugs are defined **after** `install_*` so they override the static slug helper.

## Tests

Display helpers: `tests/console_unit/test_console_*.py`. Admin BFF: `tests/api_http/test_admin_ui_bff.py`.
