# Nimbusware Admin Console (backend)

Python admin/dev control plane for inspecting runs, editing repo config, and driving operator workflows. Browser UI: [`nimbusware_admin_ui`](../nimbusware_admin_ui/) at `/v1/admin/app/`. End users: [`nimbusware_maker`](../nimbusware_maker/README.md) at `/v1/maker/app/`.

## Running

| Entry | Command |
|-------|---------|
| Admin web UI | `nimbusware-admin` or `nimbusware-run --admin` |
| API only | `poetry run nimbusware-api` then open `http://127.0.0.1:8000/v1/admin/app/` |

Build Admin SPA before packaging: `cd packages/nimbusware_admin_ui && npm ci && npm run build`.

### Environment

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_REPO_ROOT` | Frozen repo root for local YAML reads |
| `NIMBUSWARE_API_BASE` | API base for run list, detail, timeline |
| `NIMBUSWARE_ADMIN_TOKEN` | Admin gate (`X-Nimbusware-Admin-Token`) |
| `NIMBUSWARE_UI_BACKEND` | `web` (default; pywebview opens `/v1/admin/app/`) |

## Layout

```
nimbusware_console/
├── services/                 # HTTP clients to /v1 (runs, chat, config, ollama, …)
├── components/               # Shared explainer panel + operator metrics helpers
├── explainer_core/           # metrics_scaffold, workflow_payload_header, yaml_version_caption, exports
├── integration_adapter_writer_workflow_explainer/  # 7th workflow explainer package
├── *_display.py              # Top-level display facades (import these from BFF routes)
├── operator_chat_core.py     # Operator chat command handling
├── admin_gate.py             # Token gate helpers
├── integrator_gate/          # Integrator gate latest delta + history
├── integrator_preview/       # Integrator YAML preview + merge captions
├── integrator_threshold_explainer/
├── bundle_catalog/           # Local catalog search, FAISS status, tags rollup
├── persona_catalog/          # Persona pairings, summary metrics, export
├── run_escalated/            # Escalation row formatters
├── security_scan_on_verify/  # Security scan timeline + linter alignment
├── self_refinement/          # Self-refinement marker history
├── *_workflow_explainer/     # Per-workflow operator explainers (metrics + payload)
└── enterprise_console*.py    # Enterprise fleet formatters (Admin Fleet tab)
```

## Display modules (facade entry points)

| Module | Admin surface |
|--------|---------------|
| `findings_display.py` | Run findings panel |
| `critic_matrix_display.py` | Live critic matrix |
| `critic_reliability_display.py` | Critic reliability drilldown |
| `integrator_gate_display.py` | Integrator gate status |
| `run_list_pagination_display.py` | Run list + timeline captions |
| `run_escalated_display.py` | Escalation history |
| `preflight_history_display.py` | Preflight cross-run history |
| `preflight_cross_run_display.py` | Preflight trend metrics |
| `memory_display.py` | Memory influence table |
| `bundle_memory_display.py` | Bundle-scoped memory |
| `prune_status_display.py` | Memory prune inventory |
| `scraper_fetch_display.py` | Scraper stage artifacts |
| `micro_slice_packet_display.py` | Slice context packet |
| `agent_evaluator_display.py` | Agent evaluator workflow |
| `universal_critique_timeline_display.py` | Universal critique timeline |
| `self_refinement_display.py` | Self-refinement markers |
| `security_scan_on_verify_display.py` | Security scan on verify |
| `phase3_critique_display.py` | Phase-3 critique panels |
| `persona_assignment_display.py` | Persona assignment summary |

Nested packages (`bundle_catalog/`, `persona_catalog/`, `integrator_*`, `*_workflow_explainer/`) hold split implementation modules kept under the 400-line CI limit. Prefer importing the top-level `*_display.py` or `*_workflow_explainer.py` facade unless extending internals.

## Tests

Display helpers: `tests/console/test_console_*.py`. Admin BFF: `tests/api/test_admin_ui_bff.py`.
