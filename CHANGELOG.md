# Changelog

## 0.2.0 - 2026-09-19

- Added host-independent MCP server using the official MCP Python SDK v2.
- Added seven lifecycle tools for run/agent creation, updates, events, completion and inspection.
- Verified MCP 2026-07-28 interoperability in-memory, over real stdio, and over Streamable HTTP.
- Added Codex, Claude Code, Cursor and OpenCode installer/config support.
- Added generic MCP configuration output for other hosts.
- Added generic command adapter for software without MCP support.
- Added software-independent event writer shared by adapters.
- Added Streamable HTTP mode for remote/cloud host integration.
- Reframed CodePilot as one adapter rather than the AgentHub core.

## 0.1.1 - 2026-09-19

- Added CodePilot-native `AI团队` entry and in-app AgentHub panel.
- Added CORS support for the local HTTP/SSE bridge.
- Added CodePilot UI self-heal while AgentHub is running.
- Added Windows per-user autostart installer and verification.
- Added clean UI uninstall support.
- Removed the need for a desktop AgentHub shortcut in normal use.
- Verified the injected button in rendered CodePilot DOM with a headless Chromium load.

## 0.1.0 - 2026-09-19

- Added portable AgentHub JSONL event protocol v0.1.
- Added dependency-free Python HTTP/SSE core.
- Added real-time text dashboard with latest-run following.
- Added legacy reader for existing CodePilot TeamRuns.
- Added installable/rollbackable CodePilot team-orchestrator adapter.
- Added real-time lifecycle events for run creation, routing, start, completion and failure.
- Added failure-reason extraction from Codex child JSONL.
- Added simulator and live-state regression tests.
- Reserved optional trace/span correlation fields for future visual tracing.
