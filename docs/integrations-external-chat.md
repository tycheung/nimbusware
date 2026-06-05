# External chat integrations (§20.5 boundary)

Nimbusware is a **coding factory**, not a general-purpose chat workspace. Email, calendar, and deep-research UIs are **out of scope** for core product.

## Supported integration

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

### Configuration

Set `NIMBUSWARE_WEBHOOK_SECRET` in `.env` (install scope). External systems send:

`X-Nimbusware-Webhook-Secret: <value>`

Without a secret, the webhook requires `X-Nimbusware-Admin-Token` (same as Admin Console).

## Alternatives

- **Admin operator chat** — `POST /v1/admin/ui/operator-chat/message`
- **IDE bridge** — `nimbusware-mcp` ([ide-bridge.md](ide-bridge.md))
