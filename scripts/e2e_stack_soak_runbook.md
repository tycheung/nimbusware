# Full UI replay stack soak

Long-run validation for campaign + launch eval over a live API subprocess with embedded dispatch worker.

## Local run

```powershell
poetry run pytest tests/e2e/journeys/test_full_replay_stack_soak.py -m "e2e_stack and slow" -q
```

Requires no Postgres (uses in-memory store in subprocess). Expect ~60s runtime.

## What it checks

1. `start_api_subprocess` with `NIMBUSWARE_EMBED_DISPATCH_WORKER=1`
2. Autonomous `campaign_micro_slice` run reaches maker progress with slices
3. `POST /maker/launch-eval` returns scorecard with `attach_context.prompt_id=basic_crm`

## CI

Opt-in only (`@pytest.mark.slow`); default PR unit job excludes slow tests. Weekly or pre-release: run with `-m slow` after exporting `NIMBUSWARE_REPO_ROOT`.
