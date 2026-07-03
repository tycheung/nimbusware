# auth

Local **collaborative-chat authentication** when `NIMBUSWARE_COLLAB_ENABLED=1`.

## Responsibility

- User registration and login (`auth/store.py`, `auth/models.py`)
- Session tokens for multi-participant Maker chat
- Wired through `api` deps (`UserStore`, `CollabStore`) and chat routes

Enterprise edition uses IAM API keys instead of this package for route auth. See [collaborative-chat.md](../../docs/collaborative-chat.md).

## Related

- [`maker/chat/`](../maker/chat/) — chat session persistence
- [`iam`](../iam/) — Enterprise tenants and API keys
- [packages/README.md](../README.md)
