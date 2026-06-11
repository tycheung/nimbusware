# Published benchmark snapshots

Optional marketing artifacts consumed by Admin **Metrics** (`GET /v1/platform/analytics/competitive-summary`).

| File | Producer |
|------|----------|
| `latest_swe_bench.json` | `scripts/swe_bench_harness.py --run --json` or `scripts/publish_benchmark_snapshots.py` |
| `latest_factory_weekly.json` | `scripts/run_factory_weekly_ci.py` or `scripts/publish_benchmark_snapshots.py` |
| `latest_critic_reliability.json` | `scripts/publish_benchmark_snapshots.py` (fleet critic metrics snapshot) |

Regenerate locally:

```bash
poetry run python scripts/publish_benchmark_snapshots.py
```

Committed snapshots use repo-relative paths only. CI may upload fresher artifacts without committing them.
