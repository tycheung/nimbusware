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
| `ollama_presets.py` | Quality / Balanced / Speed preset hints per row |
| `pressure.py` | `sample_pressure` → ok / warn / throttle / block; `should_defer_memory_rebuild` |
| `audit.py` | Append `hardware.profile.detected` to the event store |

## API (via nimbusware_api)

- `GET /v1/platform/hardware`, `POST /v1/platform/hardware/rescan` (optional body: `emit_event`, `run_id`)
- `GET /v1/platform/models/ranked`, `POST /v1/platform/models/apply-preset`
- `GET /v1/platform/models/dependencies`

## Fixtures and pressure

- `NIMBUSWARE_HW_FIXTURE=weak|medium|strong` — deterministic profile in CI
- `HERMES_PRESSURE_DEGRADE_STUB` — when RAM is blocked, skip LLM paths (default on)
- Memory index rebuild at run start skips when pressure is warn/throttle/block (governor cap)

## Attribution

Fit heuristics are adapted from [Odysseus](https://github.com/) hardware-fit patterns (hwfit). A future optional `llmfit` dependency may deepen scoring; the offline catalog is the default.
