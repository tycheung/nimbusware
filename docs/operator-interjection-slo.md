# Interjection latency SLO

Operator interjection messages (`[patch]`, `[steer]`, `[skip]`, `[build]`) are queued per run and
drained at the start of each slice cycle.

## Target

**Drain within one slice cycle** of enqueue — i.e. before the next `slice.plan` stage starts without
an `interjection.drained` event in between.

## Observability

| Surface | Path |
|---------|------|
| Live queue | `GET /v1/runs/{id}/interjection-queue` |
| Audit events | `interjection.enqueued`, `interjection.drained` on the run timeline |
| Admin explain | `GET /v1/runs/{id}/timeline/interjection/explain` |
| Maker ribbons | Progress tab interjection ribbon (`data-testid` operator ribbons) |

When the SLO is breached, the Admin timeline **Interjection SLO** accordion shows overdue items and
any pending live queue depth.

## Operator actions

- Use **Next** priority for urgent steering; **Last** to defer to end of cycle.
- `[steer]` injects volatile guidance into the next slice plan without a full patch lane.
- `[patch]` escalates to head patch slice; `[skip]` defers the current backlog slice.

Related: [integrations-external-chat.md](integrations-external-chat.md) for webhook steering.
