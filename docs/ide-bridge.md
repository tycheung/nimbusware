# IDE bridge (MCP)

The `nimbusware-mcp` command exposes a stdio MCP server so editors (for example Cursor) can query run status, theater messages, slice diffs, approve plans, trigger campaign compaction, and mirror Maker **Chat** intent routing (classify, patch lane, interjection steering, conversation fork/branch) against a running Nimbusware API. See [ADR 020](adr/020-unified-chat-work-type-routing.md) and [ADR 021](adr/021-conversation-dag-branching.md).

## Requirements

- API reachable at `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`)
- Optional `NIMBUSWARE_API_KEY` for Enterprise user scope

## Cursor / VS Code configuration

Copy-paste into **Cursor → Settings → MCP** or VS Code `mcp.json` (under 5 minutes with API already running):

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

Recommended editor extensions (optional): Python, REST Client, GitLens — Nimbusware does not ship inline completion; use MCP tools for governed runs.

### Patch from editor selection

Use `nimbusware_patch_from_selection` (alias of `nimbusware_patch`) with:

- `target_paths` — files in scope
- `failing_test` — pytest node id or test name from the Problems panel
- `stack_trace` — copied traceback

Example MCP args:

```json
{
  "project_id": "<uuid>",
  "message": "Fix failing auth test",
  "target_paths": ["src/auth.py", "tests/test_auth.py"],
  "failing_test": "tests/test_auth.py::test_login"
}
```

## Tools

| Tool | Description |
|------|-------------|
| `nimbusware_maker_pending` | `GET /v1/runs/{run_id}/maker/pending` |
| `nimbusware_prepare_slice` | `POST /v1/runs/{run_id}/maker/slices/prepare` |
| `nimbusware_apply_slice` | `POST /v1/runs/{run_id}/maker/slices/apply` |
| `nimbusware_skip_slice` | `POST /v1/runs/{run_id}/maker/slices/skip` |
| `nimbusware_revert_workspace` | `POST /v1/runs/{run_id}/workspace/revert` |
| `nimbusware_classify_intent` | `POST /v1/chat/classify` |
| `nimbusware_patch` | `POST /v1/runs` (patch profile) + lifecycle start/slice |
| `nimbusware_patch_from_selection` | Same as patch — IDE selection / Problems panel context |
| `nimbusware_interject` | `POST /v1/runs/{run_id}/interjection-queue` (`[patch]`/`[steer]`/`[skip]`) |
| `nimbusware_run_tests` | `POST /v1/runs/{run_id}/maker/run-tests` |
| `nimbusware_run_status` | `GET /v1/runs/{run_id}` |
| `nimbusware_run_theater` | `GET /v1/runs/{run_id}/theater` |
| `nimbusware_slice_diff` | `GET /v1/runs/{run_id}/slices/{slice_index}/diff` |
| `nimbusware_approve_plan` | `POST /v1/runs/{run_id}/maker/plan/approve` |
| `nimbusware_compact_run` | `POST /v1/runs/{run_id}/compact` (requires `NIMBUSWARE_AGENT_COMPACT=1`) |
| `nimbusware_campaign_status` | Campaign progress via `GET /v1/runs/{campaign_id}/maker-progress` |
| `nimbusware_pause_campaign` | `POST /v1/campaigns/{campaign_id}/pause` |
| `nimbusware_resume_campaign` | `POST /v1/campaigns/{campaign_id}/resume` |
| `nimbusware_backlog_summary` | `GET /v1/campaigns/{campaign_id}/backlog` |

### Chat / patch parity

| Tool | Behavior |
|------|----------|
| `nimbusware_classify_intent` | Rules-first (+ optional LLM) work-type suggestion; same as Maker Chat classify |
| `nimbusware_patch` | `POST /v1/runs` with `workflow_profile=patch`, `work_type_source=ide`, then lifecycle `start` + `slice?mode=auto` |
| `nimbusware_interject` | Enqueue steering on an active run; prefix messages with `[patch]`, `[steer]`, or `[skip]` (or rely on queue semantics) |
| `nimbusware_run_tests` | Targeted slice tests (`POST /v1/runs/{id}/maker/run-tests`) — uses `patch_context.failing_test` when set |
| `nimbusware_chat_graph` | `GET /v1/chat/sessions/{id}/graph` — full conversation DAG |
| `nimbusware_chat_fork` | `POST /v1/chat/sessions/{id}/fork` — restore from turn, retain sibling branches |
| `nimbusware_chat_select_branch` | `PUT /v1/chat/sessions/{id}/active-leaf` — navigate to branch tip |

Admin **operator chat** (`POST /v1/admin/ui/operator-chat/message`) classifies plain-language intent via the same `/chat/classify` rules, returns structured `classification` for classifier cards in the Admin SPA, and suggests `/run auto` with the mapped workflow profile.

## Status bar extension (optional)

[`extensions/nimbusware-status/`](../extensions/nimbusware-status/) is a minimal VS Code / Cursor extension that polls `GET /v1/runs/{id}` when `nimbusware.activeRunId` is set and exposes **Nimbusware: Open Maker Progress**. Build with `npm ci && npm run compile` inside the extension folder.

## Verified by

- MCP journey: `tests/e2e/journeys/test_mcp_ide_parity_journey.py`
- Wiring gate: `tests/web/test_parity_ide_wiring.py`
- Extension manifest: `tests/unit/test_vscode_extension_manifest.py`

Related read APIs (HTTP only today): `GET /v1/runs/{run_id}/context_budget` for advisory context utilization. See [operator-settings.md](operator-settings.md) and [adr/007-context-compaction.md](adr/007-context-compaction.md).
