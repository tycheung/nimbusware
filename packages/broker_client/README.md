# broker_client

HTTP and MCP clients for the local **SwissArmyNoife** broker during Nimbusware peel
(`sak401` / `sak402` / Phase 9).

## Usage

```python
from broker_client import (
    BrokerClient,
    BrokerMcpClient,
    bind_llm_chat,
    broker_llm_enabled,
    llm_chat_via_broker,
    select_backend,
    select_llm_backend,
)

# HTTP admin (sak401)
client = BrokerClient()  # or BrokerClient("http://127.0.0.1:8787")
client.health()
client.list_modules()
client.get_module("demo.wasm")

# MCP tools (sak402-a/b/c; initialize session + tools/list)
mcp = BrokerMcpClient()
mcp.ping()
mcp.list_tools()  # or mcp.tools_list()
mcp.call_tool("llm_chat", {"messages": [{"role": "user", "content": "hi"}]})

# Stage bind helper (sak410-a)
if select_llm_backend() == "broker":
    plan = bind_llm_chat(client)
    reply = llm_chat_via_broker([{"role": "user", "content": "hi"}])
```

## Environment

| Variable | Purpose | Default |
|----------|---------|---------|
| `NIMBUSWARE_BROKER_HTTP` | http-admin base URL | `http://127.0.0.1:8787` |
| `NIMBUSWARE_BROKER_MCP` | Streamable HTTP MCP URL | `http://127.0.0.1:8080/mcp` |
| `NIMBUSWARE_BROKER_TOKEN` | Bearer token (HTTP admin + MCP) | unset |
| `NIMBUSWARE_BROKER_LLM` | Dual-run LLM flag (`1` / `true` / `yes`) | off |
| `NIMBUSWARE_BROKER_SANDBOX` | Dual-run sandbox | off |
| `NIMBUSWARE_BROKER_TOOLS` | Dual-run fs/shell tools | off |
| `NIMBUSWARE_BROKER_MEMORY` | Dual-run memory index/search | off |
| `NIMBUSWARE_BROKER_RESEARCH` | Dual-run research fetch/brief | off |
| `NIMBUSWARE_BROKER_EGRESS` | Dual-run egress check/fetch | off |
| `NIMBUSWARE_BROKER_COMPUTE` | Dual-run compute node/work | off |

Cross-repo flag contract: [Agentic docs/dual-run-flags.md](../../../docs/dual-run-flags.md).

## Modules

| Module | Role |
|--------|------|
| `client.py` | HTTP admin `BrokerClient` (`health`, `list_modules`, `get_module`, capacity/compute) |
| `http.py` | URL/token/auth header helpers (private) |
| `http_get.py` | HTTP GET JSON transport (`get_json`; lazy re-export from `http` for compat) |
| `mcp_client.py` | Streamable HTTP MCP facade (`BrokerMcpClient`, `resolve_mcp_url`) |
| `mcp_rpc.py` | JSON-RPC payload, session capture, and response parsing |
| `flags.py` | Dual-run env flags + `select_backend` |
| `stage_bind/` | Domain bind helpers + unified registry (`sak410-d`) |
| `stage_bind/registry.py` | `DOMAIN_BINDS`, `bind_plan(domain)`, `list_bind_domains()` |
| `llm_hook.py` | Orchestrator seam stub (`sak403-b`) |

## Stage bind registry (`sak410-d`)

All peel domains register a `bind_*` helper in `stage_bind/registry.py`. Use
`bind_plan(domain)` for soak tooling and orchestrator stage wiring instead of importing each
module directly:

```python
from broker_client import bind_plan, list_bind_domains, try_broker_shell_exec

for domain in list_bind_domains():
    if select_backend(domain) == "broker":
        plan = bind_plan(domain)  # raises BrokerDisabled when flag off

# Optional dual-run fallback (tools shell): returns None when disabled or on error
out = try_broker_shell_exec(["echo", "hi"])
```

| Domain | `bind_plan` helper | Dual-run flag |
|--------|-------------------|---------------|
| `llm` | `bind_llm_chat` | `NIMBUSWARE_BROKER_LLM` |
| `sandbox` | `bind_sandbox_exec` | `NIMBUSWARE_BROKER_SANDBOX` |
| `tools` | `bind_tools_shell` | `NIMBUSWARE_BROKER_TOOLS` |
| `memory` | `bind_memory_search` | `NIMBUSWARE_BROKER_MEMORY` |
| `research` | `bind_research_fetch` | `NIMBUSWARE_BROKER_RESEARCH` |
| `egress` | `bind_egress_check` | `NIMBUSWARE_BROKER_EGRESS` |
| `compute` | `bind_compute_work` | `NIMBUSWARE_BROKER_COMPUTE` |

**Note:** Streamable HTTP MCP negotiates session via `initialize` (`sak402-b`); live broker soak
remains a separate gate from unit-tested JSON-RPC wiring.
