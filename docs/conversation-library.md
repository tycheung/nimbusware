# Conversation library (v1.2 Track B8 — stub)

Organize many chat sessions per project without merging threads. Each session remains one shared conversation; library features reduce one-by-one invites.

## Concepts

| Entity | Purpose |
|--------|---------|
| **Folder** | Tree of sessions within a project (e.g. `Q2 patches`) |
| **Tag** | Flat labels on sessions (`security`, `frontend`) |
| **User group** | Bulk grant target (Enterprise directory) |
| **Access grant** | ACL: folder/tag/session → user or group + participant role |

## Session metadata (shipped stub)

`nimbusware_chat_session.metadata` JSONB:

```json
{ "folder": "Q2 patches", "tags": ["security"] }
```

API: set via session create/update when collab enabled. Full folder CRUD (`GET/POST …/chat/folders`) is planned fo1576.

## ACL merge rule (normative, not yet implemented)

Highest participant role wins at finest grain: direct session grant > tag > folder.

## UI (planned)

- Chat library sidebar (`data-testid="maker-chat-library"`)
- Invite modal v2 tabs: session · group · folder · tag

See ADR 023 and `alllms.md` Phase B8 for full epic list.
