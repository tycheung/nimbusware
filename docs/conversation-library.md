# Conversation library (v1.2 Track B8)

Organize many chat sessions per project without merging threads. Each session remains one shared conversation; library features reduce one-by-one invites.

## Concepts

| Entity | Purpose |
|--------|---------|
| **Folder** | Tree of sessions within a project (e.g. `Q2 patches`) |
| **Tag** | Flat labels on sessions (`security`, `frontend`) |
| **User group** | Bulk grant target (Enterprise directory) |
| **Access grant** | ACL: folder/tag/session → user or group + participant role |

## APIs (shipped)

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST/PATCH/DELETE | `/v1/chat/folders` | Folder CRUD |
| GET/POST | `/v1/chat/groups` | User group CRUD |
| POST | `/v1/chat/groups/{id}/members` | Group membership |
| GET/POST/DELETE | `/v1/chat/access-grants` | Bulk ACL grants |
| PUT | `/v1/chat/sessions/{id}/library` | Move session to folder; set tags |
| GET | `/v1/chat/sessions/{id}/effective-role` | Merged ACL role for a user |

## ACL merge rule

Highest participant role wins at finest grain: direct session grant > folder > tag (`session_admin` > `session_write` > `session_read`).

## UI

Maker Chat **Library** sidebar (`data-testid="maker-chat-library"`) — folder tree, tag filter, session list. Module: `chat_library_ui.js`.
