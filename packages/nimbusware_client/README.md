# Nimbusware Client

Shared HTTP client for Admin Console, Maker, and scripts talking to `nimbusware_api`.

## Usage

```python
from nimbusware_client.http import get, post, get_response, HTTPError
```

- Base URL: `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`)
- User auth: `NIMBUSWARE_API_KEY` → `X-Nimbusware-Api-Key`
- Admin auth: `NIMBUSWARE_ADMIN_TOKEN` → `X-Nimbusware-Admin-Token`

Problem+JSON error bodies are parsed via `problem_message()`. Console and Maker must not import `httpx` directly (see `tests/unit/test_import_graph.py`).
