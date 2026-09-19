# Universal integrations

AgentHub v0.2 adds a software-independent MCP server and a generic command adapter.

The CodePilot integration remains available, but it is now only one adapter. The core event protocol and MCP tools are shared by every supported host.

## Install MCP dependency

From the AgentHub repository:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

The MCP server command is:

```text
<AgentHub>\.venv\Scripts\python.exe <AgentHub>\agenthub\mcp_server.py
```

The server uses stdio and exposes these tools:

- `create_run`
- `create_agent`
- `update_agent`
- `emit_event`
- `complete_run`
- `get_run`
- `list_runs`

## Codex / ChatGPT desktop / Codex IDE

Codex supports local stdio MCP servers.

```bat
codex mcp add agenthub -- C:\path\to\AgentHub\.venv\Scripts\python.exe C:\path\to\AgentHub\agenthub\mcp_server.py
```

Verify:

```bat
codex mcp list
```

## Claude Code

```bat
claude mcp add agenthub -- C:\path\to\AgentHub\.venv\Scripts\python.exe C:\path\to\AgentHub\agenthub\mcp_server.py
```

For user-wide installation:

```bat
claude mcp add agenthub --scope user -- C:\path\to\AgentHub\.venv\Scripts\python.exe C:\path\to\AgentHub\agenthub\mcp_server.py
```

Verify with `claude mcp list` or `/mcp`.

## Cursor

Create or merge `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agenthub": {
      "type": "stdio",
      "command": "C:\\path\\to\\AgentHub\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\AgentHub\\agenthub\\mcp_server.py"]
    }
  }
}
```

Cursor CLI and the editor share the MCP configuration.

## OpenCode

```bat
opencode mcp add agenthub -- C:\path\to\AgentHub\.venv\Scripts\python.exe C:\path\to\AgentHub\agenthub\mcp_server.py
```

Or configure a local MCP server in `opencode.jsonc`.

## VS Code and other MCP hosts

Use the same stdio command:

```text
command: <AgentHub>/.venv/Scripts/python.exe
args:    <AgentHub>/agenthub/mcp_server.py
```

Any MCP host that supports a local stdio server can use AgentHub without a host-specific core implementation.

## Streamable HTTP for remote/cloud hosts

Run:

```bat
.venv\Scripts\python.exe agenthub\mcp_server.py --transport streamable-http --port 8876
```

Connect the host to:

```text
http://127.0.0.1:8876/mcp
```

Keep the default localhost binding for local use. If you deploy AgentHub on a real network hostname, configure transport security and authentication before exposing it.

## Software without MCP

Use the generic command adapter:

```bat
py -3 adapters\generic\command_adapter.py ^
  --title "My task" ^
  --agent worker ^
  --role coding ^
  --task "Implement feature" ^
  --model my-model ^
  -- your-agent-cli --some-flag
```

The wrapped process is streamed into the same AgentHub lifecycle protocol. Multiple commands may join the same run by passing `--run-id`.

## Design rule

Host-specific adapters translate native lifecycle events into the AgentHub protocol. They must not own visualization state.

```text
Codex ---------\
Claude Code ----\
Cursor ----------> MCP / Adapter ---> AgentHub Protocol ---> AgentHub Core ---> Text/Graph/Animation UI
OpenCode -------/
Other CLI -----/
```

This keeps future visualizations portable. A new host needs only an adapter, not a new dashboard.
