# Replay-from checkpoint runbook

Use `POST /v1/runs/{id}/replay-from` to overlay compaction policy and resume campaign work from a
`store_seq` checkpoint.

## When to use

- Workflow or critic pack changed and you need to re-run slices from a known handoff.
- Operator reverted a bad compaction and wants the campaign driver to continue from an earlier seq.

## Steps (Admin)

1. Open **Runs → run detail** and note the target `store_seq` from the timeline accordion.
2. In **Replay from checkpoint**, enter the sequence, check **Operator ack**, and click **Replay**.
3. Confirm `run.replay.started` appears on the timeline; campaign runs enqueue a new tick when applicable.

## API

```http
POST /v1/runs/{run_id}/replay-from
Content-Type: application/json

{
  "from_store_seq": 42,
  "operator_ack": true,
  "compact_enabled": true,
  "ignore_compaction_ids": [],
  "reason": "policy regression check"
}
```

## Related

- [eval-tuning-guide.md](../eval-tuning-guide.md) — compaction scopes
- ADR [007-context-compaction.md](../adr/007-context-compaction.md)
