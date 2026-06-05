# nimbusware_research

Research briefs, stitch transplant stages, and outcome analytics.

## Modules

| Module | Role |
|--------|------|
| `stages.py` / `stages_stitch.py` | Research and stitch pipeline stages |
| `stitch_read_model.py` | Stitch snapshot helpers from events |
| `stitch_outcome_stats.py` | Transplant pass-rate aggregate from event store |

## API

| Endpoint | Audience | Purpose |
|----------|----------|---------|
| `GET /v1/runs/{id}/stitch-summary` | User (Maker Review) | Stitch transplant snapshot for one run |
| `GET /v1/platform/analytics/stitch-outcomes` | User / Admin | Recent runs with `stitch.applied` scored against subsequent gate outcomes |
