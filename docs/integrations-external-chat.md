# External chat integrations (§20.5 boundary)

Nimbusware ships a **minimal in-product chat workspace** on Maker **Chat** (`#/chat`): persistent sessions, intent classification, work-type routing, fork/branch navigation, mid-run steering, and a live run-theater feed when `?run_id=` is set. See [ADR 020](adr/020-unified-chat-work-type-routing.md) and [ADR 021](adr/021-conversation-dag-branching.md).

**This document** covers the **external** webhook only — forwarding operator commands from Slack, Teams, or other tools. It complements (does not replace) Maker Chat and Admin operator chat.

## In-product vs external

| Surface | Role |
|---------|------|
| **Maker Chat** (`#/chat`) | Primary operator workspace — sessions, DAG fork/branch, classify → start run, inline theater digest, escalation chips |
| **Progress** (`#/progress`) | Full run theater (`actor_display`, severity, evidence bodies, export) and operator ribbons |
| **Admin operator chat** | `POST /v1/admin/ui/operator-chat/message` — same classifier, admin SPA |
| **IDE bridge (MCP)** | `nimbusware-mcp` — chat graph/fork, patch, interject ([ide-bridge.md](ide-bridge.md)) |
| **External webhook** (below) | Headless `/run`, `/status`, interjection prefixes on `last_run_id` |

### Chat workspace — shipped vs drill-down

| Capability | Maker Chat | Progress |
|------------|------------|----------|
| User turns + classifier / system replies | Yes | — |
| Fork (“Restore from here”) + sibling branch picker | Yes (flat list; DAG via `GET .../graph`) | — |
| Session resume (one session per browser; Settings toggle) | Yes | — |
| List sessions API (`GET /v1/chat/sessions?project_id=`) | API only — no session browser UI yet | — |
| Live run theater | Yes — SSE digest (last 12 lines, truncated text; no per-role labels) | Yes — full theater with `actor_display`, severity, expandable `body_md` |
| Operator ribbons (interjection, autopilot, dev-env, council) | Steering via message when `?run_id=` set | Yes |

**Out of scope for core product:** general collaboration (email, calendar, Slack/Teams as the product UI). Use the webhook or MCP to **steer** runs from those tools; do not expect a full Slack clone inside Nimbusware.

## Supported integration (external webhook)

Forward **operator commands** from Slack, Teams, or other tools via webhook:

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/v1/integrations/external-chat` | Admin token |
| `POST` | `/v1/integrations/external-chat/webhook` | `X-Nimbusware-Webhook-Secret` or admin token |

### Webhook body

```json
{
  "text": "/run micro_slice",
  "source": "slack",
  "session_id": "channel-123"
}
```

Response includes `reply` (operator chat handler output) and `last_run_id` when a run was started.

### Steering an active run

After `/run` (or a natural-language start), send interjection prefixes on the same webhook session:

| Prefix | Effect |
|--------|--------|
| `[patch]` | Head patch slice from chat |
| `[steer]` | Volatile guidance on next slice plan |
| `[skip]` | Defer current backlog slice |
| `[build]` | Promote to campaign from chat |

`/status` returns pending interjection queue depth plus a micro-slice timeline summary for
`last_run_id`.

See [operator-interjection-slo.md](operator-interjection-slo.md) for drain latency SLO.

### Configuration

Set `NIMBUSWARE_WEBHOOK_SECRET` in `.env` (install scope). External systems send:

`X-Nimbusware-Webhook-Secret: <value>`

Without a secret, the webhook requires `X-Nimbusware-Admin-Token` (same as Admin Console).

## Alternatives (in-product)

- **Maker Chat** — `#/chat` (default tab); full session DAG API + branch UI
- **Admin operator chat** — `POST /v1/admin/ui/operator-chat/message`
- **IDE bridge** — `nimbusware-mcp` ([ide-bridge.md](ide-bridge.md))
