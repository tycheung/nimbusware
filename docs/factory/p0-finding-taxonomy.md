# P0 finding taxonomy (factory maintenance)

Normative categories for **P0 / ship-blocking** findings surfaced during launch eval, factory gates, and maintenance passes. Use these labels in `finding.created` payloads and launch rubric rows so operators and automation share one vocabulary.

| Category | Meaning | Typical owner | Factory gate hook |
|----------|---------|---------------|-------------------|
| `security.auth` | Missing or broken authentication on user-facing routes | security critic | `put_e2e` + security scan |
| `security.injection` | SQL/command/template injection surfaces | security critic | static + PUT crawl |
| `data.migration` | Irreversible or untested schema migrations | implementer | launch eval testability |
| `api.contract` | OpenAPI/HTML surface drift vs implementation | integrator | ISM coverage + PUT E2E |
| `ops.health` | Missing health/readiness endpoints for deploy | factory cadence | PUT preview + flow runner |
| `test.coverage` | No automated test path for changed behavior | test critic | launch eval testability |
| `context.budget` | Run context exceeds advisory budget without compaction | campaign driver | compaction + replay-from |
| `factory.put` | PUT E2E flow failed on factory tier T2/T3 | factory cadence | `factory.gate` blocking list |
| `factory.ism` | Interaction surface map empty or stale | factory cadence | ISM discovery modes |
| `launch.rubric` | Aggregate launch score below campaign threshold | launch eval | `launch_eval.completed` |

**Severity:** P0 maps to `BLOCKER` or `HIGH` in finding payloads. Maintenance refactor/architecture passes may enqueue fix slices when refactor gates fail; factory `factory.gate` events carry the composite blocking list for Admin/Maker panels.

**Non-goals:** Semantic CRM validation, unbounded crawl regressions, and stretch S-track items are out of Individual v1 scope unless promoted from this taxonomy explicitly.
