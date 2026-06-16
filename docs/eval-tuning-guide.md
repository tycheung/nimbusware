# Campaign eval tuning guide

Operators tune autonomous campaign completion without changing core pipeline code. This guide complements launch eval (`POST /v1/runs/{id}/maker/launch-eval`) and completion workflow blocks in `configs/workflows/`.

## Completion workflow block

Campaign profiles (`campaign_micro_slice`, `campaign_factory_zero_touch`, `campaign_factory_t3`) embed a `completion:` block:

| Field | Effect |
|-------|--------|
| `factory_tier` | T0–T3 factory gate strictness (`configs/factory/factory_tier_policy.yaml`) |
| `e2e_on_every_n_slices` | Factory cadence interval (PUT preview + E2E + `factory.gate`) |
| `auto_launch_eval` | Emit `launch_eval.completed` on maintenance passes |
| `maintenance.refactor_every_n_slices` | Refactor maintenance cadence |
| `maintenance.architecture_every_n_slices` | Architecture maintenance cadence |

Raise `e2e_on_every_n_slices` on long campaigns to reduce PUT cost; lower it when factory regressions are frequent.

## Launch rubric thresholds

`evaluate_workspace_rubric` scores maturity/maintainability/testability from **workspace file presence** (README, pyproject, tests, etc.) plus a basic `.env` security check — not deep static analysis. Campaign goldens under `tests/fixtures/launch_eval/` document minimum aggregates per fixture workspace.

- **Tighten ship bar:** increase `min_aggregate` in golden JSON or campaign completion policy.
- **LLM dimensions:** set `NIMBUSWARE_LAUNCH_EVAL_LLM=1` for optional panel rows (Maker Review + Settings launch check).
- **Attach context:** catalog prompt matching fills `attach_context` on scorecards for repeatable factory prompts.

## Factory gates and P0 taxonomy

Composite `factory.gate` timeline stages list blocking reasons (`put_e2e_not_pass`, `ism_openapi_empty`, etc.). Map blockers to [p0-finding-taxonomy.md](p0-finding-taxonomy.md) categories when triaging.

## Replay-from and compaction

`POST /v1/runs/{id}/replay-from` with `operator_ack=true` overlays compaction policy. On campaign runs the API re-enqueues a `campaign_tick` dispatch task so the driver resumes from the checkpoint.

- `compact_enabled=false` — skip auto compaction after replay
- `ignore_compaction_ids` — treat listed compactions as inactive for budget math

## Soak and ops

24h campaign soak cadence and fleet Redis/Playwright wiring are documented under [../deploy/campaign-soak-runbook.md](../deploy/campaign-soak-runbook.md) and [../deploy/fleet-playwright-pool.md](../deploy/fleet-playwright-pool.md).
