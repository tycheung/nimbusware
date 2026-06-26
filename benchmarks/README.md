# Published benchmark snapshots

Reference metrics consumed by Admin **Metrics** (`GET /v1/platform/analytics/competitive-summary`). These are **operator-regenerated artifacts**, not live measurements on every PR unless CI gate scripts run harnesses (see `docs/security-quality-gates.md`).

| File | Producer | Notes |
|------|----------|-------|
| `latest_swe_bench.json` | `scripts/benchmarks/swe_bench_harness.py --run --json` | Local `micro_slice` fixture (`tests/fixtures/swe_bench/`); stub implement; **not** public SWE-bench |
| `latest_factory_weekly.json` | `scripts/benchmarks/run_factory_weekly_ci.py` | Weekly factory soak summary |
| `latest_critic_reliability.json` | `scripts/benchmarks/publish_benchmark_snapshots.py` | Fleet critic rollup; `runs_scanned: 0` until regenerated from real runs |
| `latest_intent_to_patch.json` | `scripts/benchmarks/measure_intent_to_patch.py --json …` | Stub-implement patch on `tiny_python_app`; median target ≤ 180s |
| `latest_classifier_acceptance.json` | `scripts/benchmarks/measure_classifier_acceptance.py --json …` | Rules-first intent classifier scenarios (no LLM) |
| `latest_archetype_metrics.json` | `scripts/benchmarks/measure_archetype_fit.py --json …` | Behavioral rubric v3 for Safe Coding, Engineer, and Enterprise archetypes (target ≥ 0.95) |
| `gate_failure_comprehension_fixture.json` | (static) | Gate-failure CTA scenarios for fo2043 harness |
| `archetype_fit_streak.json` | `scripts/ci/run_archetype_100_declaration_gate.py` | Weekly archetype-fit streak for fo2044 declaration |
| `archetype_fit_100_declaration.json` | `scripts/ci/run_archetype_100_declaration_gate.py` | Emitted when 4 consecutive green weeks + comprehension pass |

## Archetype fit (v3)

Run locally:

```bash
poetry run python scripts/benchmarks/measure_archetype_fit.py --json benchmarks/latest_archetype_metrics.json
poetry run python scripts/ci/run_archetype_fit_ci_gate.py
poetry run python scripts/benchmarks/measure_gate_comprehension.py
poetry run python scripts/ci/run_gate_comprehension_ci_gate.py
```

P3 stretch (fo2040–fo2044):

```bash
poetry run python scripts/ci/run_archetype_100_declaration_gate.py   # weekly ops; requires 4 green weeks
```

| Archetype | Static checks | Behavioral checks |
|-----------|---------------|-------------------|
| **Safe Coding** | workflow, docs, wizard UX | scaffold API, Playwright bootstrap, onboarding E2E |
| **Engineer** | collab resolver, collab-settings API, model drawer | archetype collab enable, collab routing API tests |
| **Enterprise** | enterprise bundle, compliance/audit APIs | Maker enterprise shell, enterprise journey E2E |

Regenerate all snapshots:

```bash
poetry run python scripts/benchmarks/publish_benchmark_snapshots.py
```

Committed snapshots use repo-relative paths only. Weekly workflows may upload fresher artifacts without committing them.
