# Benchmarks

Committed snapshots in [`benchmarks/`](../benchmarks/) feed Admin **Metrics** and PR CI gates.

| Snapshot | Purpose |
|----------|---------|
| `latest_swe_bench.json` | Local micro_slice regression (not public SWE-bench) |
| `latest_intent_to_patch.json` | Intent→patch timing on `tiny_python_app` |
| `latest_classifier_acceptance.json` | Chat classifier acceptance rate |
| `latest_factory_weekly.json` | Factory weekly replay |
| `latest_critic_reliability.json` | Critic reliability derived from swe_bench run |

## micro_slice regression

```bash
poetry run python scripts/benchmarks/swe_bench_harness.py --dry-run --json
poetry run python scripts/benchmarks/swe_bench_harness.py --run --json
```

Fixture: [`tests/fixtures/swe_bench/`](../tests/fixtures/swe_bench/). CI: weekly [`.github/workflows/swe_bench.yml`](../.github/workflows/swe_bench.yml).

Regenerate all snapshots: `poetry run python scripts/benchmarks/publish_benchmark_snapshots.py`

## Intent→patch

```bash
poetry run python scripts/benchmarks/measure_intent_to_patch.py
poetry run python scripts/benchmarks/measure_intent_to_patch.py --via-chat
```

PR gates: `scripts/ci/run_intent_to_patch_ci_gate.py`, `run_classifier_acceptance_ci_gate.py`.

See [benchmarks/README.md](../../benchmarks/README.md) for snapshot format details.
