# Enterprise Fleet Ollama SLI Runbook (fo206)

Sustained health-probe p95 export for fleet-wide Ollama SLO monitoring, merged with `GET /v1/preflight-history` aggregates.

## Prerequisites

- `NIMBUSWARE_EDITION=enterprise`
- Ollama reachable at `http://localhost:11434` (or set `NIMBUSWARE_FLEET_OLLAMA_SLI_BASE_URL`)

## Sustained export job

```powershell
$env:NIMBUSWARE_EDITION = "enterprise"
$env:NIMBUSWARE_FLEET_OLLAMA_SLI_SAMPLES = "60"
$env:NIMBUSWARE_FLEET_OLLAMA_SLI_INTERVAL_SEC = "5"
poetry run nimbusware-fleet-ollama-sli
```

Writes `.cache/fleet_ollama_sli.json` by default (`NIMBUSWARE_FLEET_OLLAMA_SLI_EXPORT_PATH` to override).

## Enterprise API (IAM API key required)

- `GET /v1/enterprise/fleet-ollama-sli/status` — on-disk sustained export + probe config
- `GET /v1/enterprise/fleet-ollama-sli/preflight-aggregate` — `/v1/preflight-history` + sustained SLI merge

## pytest-benchmark fleet harness

```bash
poetry install --with dev
poetry run pytest tests/benchmark/ -m benchmark --benchmark-only
```

Benchmarks the preflight-history aggregation hot path (HTTP + direct store scan).

## Operator notes

- Run sustained export on a schedule (cron / CI nightly) when Ollama is warm.
- Treat `combined_max_p95_latency_ms` in preflight-aggregate as the max of historical run p95 and latest sustained probe.
- Individual edition keeps `GET /v1/preflight-history` unchanged; enterprise aggregate is IAM-gated.
