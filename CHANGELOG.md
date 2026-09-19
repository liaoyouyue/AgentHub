# Changelog

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