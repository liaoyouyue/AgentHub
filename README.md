# AgentHub

Portable real-time multi-agent visibility layer.

AgentHub is intentionally **not tied to CodePilot**. The core reads a small append-only event protocol and exposes a local HTTP/SSE interface. IDEs and agent runtimes connect through adapters.

## Current status: v0.1.1

Working now:

- CodePilot-native **AI团队** entry and in-app panel.
- Real-time run/agent state via Server-Sent Events.
- Agent name, role, model, task, dependencies, elapsed time, result and failure reason.
- Event timeline.
- Existing CodePilot TeamRuns remain readable through a legacy compatibility reader.
- CodePilot team-orchestrator emits AgentHub protocol v0.1 events.
- CodePilot UI patch self-heals after updates while AgentHub is running.
- Windows per-user autostart keeps the AgentHub core available silently.
- No database and no cloud dependency.
- No provider credentials are stored in AgentHub events.
- Core runs with Python standard library only.

## CodePilot installation

Primary install:

```bat
py -3 adapters\codepilot\install_integration.py
```

This installs the event adapter, in-app UI patch, Windows per-user autostart, and starts the local AgentHub core.

Verify:

```bat
py -3 adapters\codepilot\install_integration.py --verify
```

Uninstall:

```bat
py -3 adapters\codepilot\install_integration.py --uninstall
```

The CodePilot integration does **not** change Smart Router, providers, credentials, model routing rules, or CodePilot themes.

## Standalone / debugging

The built-in web dashboard remains available for debugging or non-CodePilot adapters:

```bat
py -3 server.py --port 8765 --open
```

Default local URL:

```text
http://127.0.0.1:8765/
```

`start-agenthub.cmd` is kept only as a local fallback/debug launcher. The normal CodePilot workflow does not require a desktop shortcut or separate window.

## Protocol

See `docs/PROTOCOL.md`.

Each run contains an append-only `agenthub-events.jsonl`. Any future adapter can produce the same events.

Example:

```json
{"version":"0.1","type":"agent.started","run_id":"abc","agent_id":"backend","source":"my.adapter","data":{"name":"Backend","model":"model-x","task":"Build API","status":"running"}}
```

Optional `trace_id`, `span_id`, and `parent_span_id` fields are reserved for future tracing integrations without changing the lifecycle event protocol.

## Portable data sources

By default AgentHub watches:

- `AgentHub\data\runs`
- `Documents\CodePilot\TeamRuns`

Additional run roots can be supplied with `AGENTHUB_RUN_ROOTS` using the OS path separator.

## Tests

With AgentHub running:

```bat
py -3 tests\check_ui.py
py -3 tests\test_failure_parse.py
py -3 tests\test_live.py
```

The live test verifies that an in-progress `running/waiting` state is observable before the run completes.

## Architecture

```text
Agent software / IDE
       |
     Adapter
       |
AgentHub event protocol (JSONL)
       |
 AgentHub Core
       |
 HTTP + SSE
       |
 Text UI today
 Graph / animation later
```

CodePilot is only the first adapter. The visual layer can later become a graph or animated team view without changing the event protocol.

## Planned

- Stream child-agent tool/message events while they are happening.
- Generic SDK for Python/Node adapters.
- Dependency graph view.
- Animated team view.
- Optional SQLite/indexing for large histories.
- MCP interface for control operations.
- Installer/package distribution.
- Adapters for additional agent runtimes.

## License

MIT License. See `LICENSE`.