# IDE bridge (MCP)

The `nimbusware-mcp` command exposes a stdio MCP server so editors (for example Cursor) can query run status, theater messages, slice diffs, and approve plans against a running Nimbusware API.

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
| `nimbusware_run_status` | `GET /v1/runs/{run_id}` |
| `nimbusware_run_theater` | `GET /v1/runs/{run_id}/theater` |
| `nimbusware_slice_diff` | `GET /v1/runs/{run_id}/slices/{slice_index}/diff` |
| `nimbusware_approve_plan` | `POST /v1/runs/{run_id}/maker/plan/approve` |
