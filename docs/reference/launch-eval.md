# Launch eval

Deterministic rubric v0 scores workspaces on maturity, maintainability, scalability, security, and testability. Campaign completion emits `launch_eval.completed` on the timeline.

```bash
poetry run python scripts/benchmarks/launch_eval.py path/to/workspace --json
poetry run python scripts/benchmarks/launch_eval.py path/to/workspace --json --llm
poetry run python scripts/benchmarks/launch_eval.py --matrix
poetry run python scripts/benchmarks/launch_eval.py --run-id <uuid> --json
```

## API & UI

- `POST /v1/runs/{id}/maker/launch-eval` — score attached workspace, emit timeline event
- Maker Review/Settings **Run launch check** button
- Admin run detail launch scorecard panel

Set `NIMBUSWARE_LAUNCH_EVAL_LLM=1` for Ollama-backed findings and `llm_dimensions`.

## Catalog

Prompts: [`configs/launch_eval/prompts/`](../configs/launch_eval/prompts/) and [`catalog.yaml`](../configs/launch_eval/catalog.yaml).

Golden fixtures: [`tests/fixtures/launch_eval/`](../tests/fixtures/launch_eval/). Weekly CI: [`.github/workflows/launch_eval.yml`](../.github/workflows/launch_eval.yml).

Parity wiring: [`tests/web/parity_launch_wiring.yaml`](../tests/web/parity_launch_wiring.yaml).

Tuning guide: [eval-tuning-guide.md](../eval-tuning-guide.md).
