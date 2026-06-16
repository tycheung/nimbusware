# Published benchmark snapshots

Reference metrics consumed by Admin **Metrics** (`GET /v1/platform/analytics/competitive-summary`). These are **operator-regenerated artifacts**, not live measurements on every PR unless CI gate scripts run harnesses (see `docs/security-quality-gates.md`).

| File | Producer | Notes |
|------|----------|-------|
| `latest_swe_bench.json` | `scripts/swe_bench_harness.py --run --json` | Local `micro_slice` fixture (`tests/fixtures/swe_bench/`); stub implement; **not** public SWE-bench |
| `latest_factory_weekly.json` | `scripts/run_factory_weekly_ci.py` | Weekly factory soak summary |
| `latest_critic_reliability.json` | `scripts/publish_benchmark_snapshots.py` | Fleet critic rollup; `runs_scanned: 0` until regenerated from real runs |
| `latest_intent_to_patch.json` | `scripts/measure_intent_to_patch.py --json …` | Stub-implement patch on `tiny_python_app`; median target ≤ 180s |
| `latest_classifier_acceptance.json` | `scripts/measure_classifier_acceptance.py --json …` | Rules-first intent classifier scenarios (no LLM) |

Regenerate locally:

```bash
poetry run python scripts/publish_benchmark_snapshots.py
```

Committed snapshots use repo-relative paths only. Weekly workflows may upload fresher artifacts without committing them.
