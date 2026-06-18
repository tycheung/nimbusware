# nimbusware_hw

Local hardware probe, tier classification, resource governor, model fit ranking, and mid-run pressure sampling.

## Components

| Module | Role |
|--------|------|
| `probe.py` | RAM/CPU/GPU probe; optional enterprise SSH remote (`NIMBUSWARE_HW_SSH_*`) |
| `cache.py` | Cached profile for API and Maker |
| `governor.py` | `max_system_ram_pct`, slice budgets from tier |
| `fit.py` | Rank allowlist + catalog models by fit level |
| `catalog.py` | Load `configs/hardware/model_catalog.json` |
| `catalog_sync.py` | Normalize, validate, merge catalog documents (fo549) |
| `ollama_presets.py` | Quality / Balanced / Speed preset hints per row |
| `pressure.py` | `sample_pressure` → ok / warn / throttle / block; `should_defer_memory_rebuild` |
| `audit.py` | Append `hardware.profile.detected` to the event store |

## API (via nimbusware_api)

- `GET /v1/platform/hardware`, `POST /v1/platform/hardware/rescan` (optional body: `emit_event`, `run_id`)
- `GET /v1/platform/models/ranked`, `POST /v1/platform/models/apply-preset`
- `GET /v1/platform/models/catalog-info` (version, model count, `updated_at`)
- `GET /v1/platform/models/dependencies`

## Catalog maintenance (offline-first)

Default catalog ships at `configs/hardware/model_catalog.json`. Refresh from a local Odysseus-style export:

```bash
python scripts/codegen/sync_model_catalog.py --from-json path/to/export.json --dry-run
python scripts/codegen/sync_model_catalog.py --from-json path/to/export.json --merge
python scripts/codegen/sync_model_catalog.py --from-url https://example.com/curated-models.json
```

Use `--merge` to keep existing model ids and overlay new rows. CI does not fetch URLs; operators opt in to `--from-url`.

## SSH fleet probe (Enterprise)

- `NIMBUSWARE_HW_SSH_MOCK=1` — deterministic remote profile (default in unit CI)
- `NIMBUSWARE_HW_SSH_HOST` + optional `NIMBUSWARE_HW_SSH_IDENTITY` — live probe via `ssh`
- Optional GitHub workflow: `.github/workflows/ssh_hardware_probe.yml` (`workflow_dispatch`, requires repo secrets)

PR CI keeps mock; staging operators set secrets for manual live probe runs.

## Fixtures and pressure

- `NIMBUSWARE_HW_FIXTURE=weak|medium|strong` — deterministic profile in CI
- `NIMBUSWARE_PRESSURE_DEGRADE_STUB` — when RAM is blocked, skip LLM paths (default on)
- Memory index rebuild at run start skips when pressure is warn/throttle/block (governor cap)

## Attribution

Fit heuristics are adapted from [Odysseus](https://github.com/) hardware-fit patterns (hwfit). A future optional `llmfit` dependency may deepen scoring; the offline catalog is the default.
