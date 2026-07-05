# Operator presets

Named environment bundles for common operator modes. Applied at process startup when `NIMBUSWARE_OPERATOR_PRESET` is set (see `packages/env/dotenv.py`).

Presets adjust **transport and defaults only** — workflow YAML remains the source of truth for stage graphs.

## Presets

| Preset | Use case | Key overrides |
|--------|----------|---------------|
| `offline` | CI, air-gapped smoke, no LLM | `NIMBUSWARE_USE_LLM=0`, `NIMBUSWARE_QUICK_MODE=1`, profile `quick_local` |
| `local-llm` | Developer laptop with Ollama | `NIMBUSWARE_USE_LLM=1`, Ollama base URL, profile `micro_slice` |
| `production` | Postgres-backed config, full gates | `NIMBUSWARE_CONFIG_FROM_DB=1`, profile `nimbusware_production` |

## Usage

```bash
export NIMBUSWARE_OPERATOR_PRESET=local-llm
poetry run uvicorn api.main:app
```

Windows PowerShell:

```powershell
$env:NIMBUSWARE_OPERATOR_PRESET = "offline"
.\scripts\ci_check.ps1 -SkipWeb
```

Programmatic apply (tests, bootstrap):

```python
from env.operator_presets import apply_operator_preset

trace = apply_operator_preset("offline")
```

## Related

- Implementation: `packages/env/operator_presets.py`
- Unified config trace: `packages/config/resolved_config.py` (`resolve_run_config`)
- Backlog: retire legacy env alias duplication — `PLAN_GAP.md` Phase 2 item 5
