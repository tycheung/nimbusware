# hermes_research

Research briefs, stitch transplant stages, and outcome analytics.

## Modules

| Module | Role |
|--------|------|
| `stages.py` / `stages_stitch.py` | Research and stitch pipeline stages |
| `stitch_read_model.py` | Stitch snapshot helpers from events |
| `stitch_outcome_stats.py` | Transplant pass-rate aggregate from event store |

## API

`GET /v1/platform/analytics/stitch-outcomes` — recent runs with `stitch.applied` scored against subsequent gate outcomes.
