# AgentHub

Portable real-time multi-agent observability and visualization bridge.

**AgentHub is host-independent.** CodePilot is one supported adapter, not the core product. Any AI application that supports MCP can connect to the same AgentHub server, while software without MCP can use the generic command/event adapter.

## Current status: v0.2.0 Universal

Supported integration paths:

- **CodePilot** — native `AI团队` in-app panel + team-orchestrator adapter.
- **OpenAI Codex / ChatGPT desktop / Codex IDE** — local stdio MCP.
- **Claude Code** — local stdio MCP.
- **Cursor** — local stdio MCP through `mcp.json`.
- **OpenCode** — local stdio MCP.
- **VS Code / other MCP hosts** — standard local stdio MCP.
- **Remote/cloud hosts** — Streamable HTTP MCP.
- **Software without MCP** — generic command adapter + JSONL event protocol.

The MCP server uses the official MCP Python SDK and exposes seven lifecycle tools:

`create_run`, `create_agent`, `update_agent`, `emit_event`, `complete_run`, `get_run`, `list_runs`.

## Universal MCP setup

Bootstrap the local MCP runtime:

```bat
py -3 adapters\mcp\install_host.py --host none
```

Connect a supported host:

```bat
py -3 adapters\mcp\install_host.py --host codex
py -3 adapters\mcp\install_host.py --host claude
py -3 adapters\mcp\install_host.py --host cursor
py -3 adapters\mcp\install_host.py --host opencode
```

Preview without changing host configuration:

```bat
py -3 adapters\mcp\install_host.py --host codex --dry-run --skip-bootstrap
```

For complete setup examples, see [docs/integrations/UNIVERSAL.md](docs/integrations/UNIVERSAL.md).

### Local stdio MCP

```text
<AgentHub>\.venv\Scripts\python.exe <AgentHub>\agenthub\mcp_server.py
```

### Streamable HTTP MCP

```bat
.venv\Scripts\python.exe agenthub\mcp_server.py --transport streamable-http --port 8876
```

The endpoint is:

```text
http://127.0.0.1:8876/mcp
```

## Generic command adapter

For an agent runtime that has no MCP integration:

```bat
py -3 adapters\generic\command_adapter.py ^
  --title "My task" ^
  --agent worker ^
  --role coding ^
  --task "Implement feature" ^
  --model my-model ^
  -- your-agent-cli --some-flag
```

The adapter streams process output into the same lifecycle protocol and can join an existing run with `--run-id`.

## CodePilot integration

Install:

```bat
py -3 adapters\codepilot\install_integration.py
```

Verify:

```bat
py -3 adapters\codepilot\install_integration.py --verify
```

Uninstall:

```bat
py -3 adapters\codepilot\install_integration.py --uninstall
```

The CodePilot adapter does **not** change Smart Router, providers, credentials, model-routing rules, or themes.

## Dashboard

The portable web dashboard can run independently of any host:

```bat
py -3 server.py --port 8765 --open
```

Default URL:

```text
http://127.0.0.1:8765/
```

CodePilot embeds this experience directly inside CodePilot. Other hosts can use their own UI or open the portable dashboard. Future graph/animation UIs will consume the same event protocol.

## Event protocol

See [docs/PROTOCOL.md](docs/PROTOCOL.md).

Each run contains append-only `agenthub-events.jsonl` events:

```json
{"version":"0.1","type":"agent.started","run_id":"abc","agent_id":"backend","source":"my.adapter","data":{"name":"Backend","model":"model-x","task":"Build API","status":"running"}}
```

Optional `trace_id`, `span_id`, and `parent_span_id` fields are reserved for tracing integrations.

## Architecture

```text
CodePilot --------\
Codex -------------\
Claude Code --------\
Cursor --------------> MCP / Adapter
OpenCode -----------/          |
Other MCP hosts ----/           v
Other CLI -----------> Generic Adapter
                              |
                              v
                    AgentHub Event Protocol
                              |
                              v
                         AgentHub Core
                              |
              +---------------+---------------+
              |                               |
         Text UI today                Graph/Animation later
```

A new host should only need an adapter or MCP configuration. It should never require a new AgentHub core or a separate visualization implementation.

## Tests

```bat
py -3 tests\check_ui.py
py -3 tests\test_failure_parse.py
py -3 tests\test_live.py
.venv\Scripts\python.exe tests\test_mcp.py
.venv\Scripts\python.exe tests\test_mcp_stdio.py
.venv\Scripts\python.exe tests\test_mcp_http.py
```

The MCP tests verify in-memory, real stdio subprocess, and Streamable HTTP transports.

## Roadmap

- Native event adapters for more agent runtimes and IDE hook systems.
- Dependency graph view.
- Animated team workspace.
- Tool/model span tracing.
- Optional SQLite indexing for large histories.
- Packaged installers and marketplace/plugin distribution.
- Remote authenticated MCP deployment profile.

## License

MIT License. See `LICENSE`.
