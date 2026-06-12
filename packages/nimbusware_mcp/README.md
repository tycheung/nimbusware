# nimbusware_mcp

Stdio MCP server (`nimbusware-mcp`) for IDE integration with a running Nimbusware API.

## Configuration

See [docs/ide-bridge.md](../../docs/ide-bridge.md) for Cursor MCP settings. Requires `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`).

## Tools

| Tool | API |
|------|-----|
| `nimbusware_maker_pending` | `GET /v1/runs/{run_id}/maker/pending` |
| `nimbusware_prepare_slice` | `POST /v1/runs/{run_id}/maker/slices/prepare` |
| `nimbusware_apply_slice` | `POST /v1/runs/{run_id}/maker/slices/apply` |
| `nimbusware_skip_slice` | `POST /v1/runs/{run_id}/maker/slices/skip` |
| `nimbusware_revert_workspace` | `POST /v1/runs/{run_id}/workspace/revert` |
| `nimbusware_classify_intent` | `POST /v1/chat/classify` |
| `nimbusware_patch` | `POST /v1/runs` (patch profile) + lifecycle start/slice |
| `nimbusware_patch_from_selection` | Same as `nimbusware_patch` — IDE selection / Problems panel context |
| `nimbusware_interject` | `POST /v1/runs/{run_id}/interjection-queue` |
| `nimbusware_run_tests` | `POST /v1/runs/{run_id}/maker/run-tests` |
| `nimbusware_run_status` | `GET /v1/runs/{run_id}` |
| `nimbusware_run_theater` | `GET /v1/runs/{run_id}/theater` |
| `nimbusware_slice_diff` | `GET /v1/runs/{run_id}/slices/{slice_index}/diff` |
| `nimbusware_approve_plan` | `POST /v1/runs/{run_id}/maker/plan/approve` |
| `nimbusware_compact_run` | `POST /v1/runs/{run_id}/compact` |
| `nimbusware_campaign_status` | `GET /v1/runs/{campaign_id}/maker-progress` |
| `nimbusware_pause_campaign` | `POST /v1/campaigns/{campaign_id}/pause` |
| `nimbusware_resume_campaign` | `POST /v1/campaigns/{campaign_id}/resume` |
| `nimbusware_backlog_summary` | `GET /v1/campaigns/{campaign_id}/backlog` |
| `nimbusware_chat_graph` | `GET /v1/chat/sessions/{id}/graph` |
| `nimbusware_chat_fork` | `POST /v1/chat/sessions/{id}/fork` |
| `nimbusware_chat_select_branch` | `PUT /v1/chat/sessions/{id}/active-leaf` |

Manual compaction is gated by `NIMBUSWARE_AGENT_COMPACT` (default on). It calls the same `maybe_emit_compaction_event` entrypoint as automatic post-handoff compaction.

Implementation: [`tools.py`](tools.py), [`server.py`](server.py), [`cli.py`](cli.py).
