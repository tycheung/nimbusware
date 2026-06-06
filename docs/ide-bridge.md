# IDE bridge (MCP)

The `nimbusware-mcp` command exposes a stdio MCP server so editors (for example Cursor) can query run status, theater messages, slice diffs, approve plans, and trigger campaign compaction against a running Nimbusware API.

## Requirements

- API reachable at `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`)
- Optional `NIMBUSWARE_API_KEY` for Enterprise user scope

## Cursor configuration

Add to your MCP settings:

```json
{
  "mcpServers": {
    "nimbusware": {
      "command": "nimbusware-mcp",
      "env": {
        "NIMBUSWARE_API_BASE": "http://127.0.0.1:8000/v1"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `nimbusware_maker_pending` | `GET /v1/runs/{run_id}/maker/pending` |
| `nimbusware_prepare_slice` | `POST /v1/runs/{run_id}/maker/slices/prepare` |
| `nimbusware_apply_slice` | `POST /v1/runs/{run_id}/maker/slices/apply` |
| `nimbusware_skip_slice` | `POST /v1/runs/{run_id}/maker/slices/skip` |
| `nimbusware_run_status` | `GET /v1/runs/{run_id}` |
| `nimbusware_run_theater` | `GET /v1/runs/{run_id}/theater` |
| `nimbusware_slice_diff` | `GET /v1/runs/{run_id}/slices/{slice_index}/diff` |
| `nimbusware_approve_plan` | `POST /v1/runs/{run_id}/maker/plan/approve` |
| `nimbusware_compact_run` | `POST /v1/runs/{run_id}/compact` (requires `NIMBUSWARE_AGENT_COMPACT=1`) |
| `nimbusware_campaign_status` | Campaign progress via `GET /v1/runs/{campaign_id}/maker-progress` |
| `nimbusware_pause_campaign` | `POST /v1/campaigns/{campaign_id}/pause` |
| `nimbusware_resume_campaign` | `POST /v1/campaigns/{campaign_id}/resume` |
| `nimbusware_backlog_summary` | `GET /v1/campaigns/{campaign_id}/backlog` |

Related read APIs (HTTP only today): `GET /v1/runs/{run_id}/context_budget` for advisory context utilization. See [operator-settings.md](operator-settings.md) and [adr/007-context-compaction.md](adr/007-context-compaction.md).
