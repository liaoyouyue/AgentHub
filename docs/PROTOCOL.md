# AgentHub Event Protocol v0.1

AgentHub uses an append-only JSON Lines event stream. Each line is one UTF-8 JSON object.

## Envelope

```json
{
  "version": "0.1",
  "id": "evt_...",
  "ts": "2026-09-19T09:00:00.000+08:00",
  "type": "agent.started",
  "run_id": "20260919-090000-abc123",
  "agent_id": "backend",
  "source": "codepilot.team-orchestrator",
  "data": {}
}
```

Required fields: `version`, `id`, `ts`, `type`, `run_id`, `source`.
`agent_id` is required for agent-scoped events.

Optional forward-compatible correlation fields: `trace_id`, `span_id`, `parent_span_id`.
They are not required by the v0.1 dashboard, but adapters may provide them when bridging an
existing tracing system. Point-in-time lifecycle changes stay as events; future duration-bearing
model/tool operations may be represented as spans without changing the lifecycle event names.

## Lifecycle events

- `run.created`
- `agent.created`
- `agent.routing`
- `agent.routed`
- `agent.started`
- `agent.message`
- `agent.waiting`
- `agent.blocked`
- `agent.completed`
- `agent.failed`
- `run.completed`
- `run.failed`

The UI must ignore unknown event types so newer adapters remain backward compatible.

## State reconstruction

A dashboard reconstructs current state by replaying events in timestamp/file order. Events are immutable; corrections are emitted as newer events.

## Design rules

1. Keep transport independent from the agent framework.
2. Treat state changes/checkpoints as events; long-running operations may later map to trace spans.
3. Keep human-readable messages separate from structured attributes.
4. Never require model/provider credentials in the event stream.
5. Adapters may add namespaced fields inside `data`.
6. The protocol must remain useful without AgentHub UI.

## v0.1 common data fields

Run: `title`, `workspace`, `status`.
Agent: `name`, `role`, `task`, `model`, `requested_model`, `status`, `elapsed_sec`, `message`, `error`, `depends_on`.

This protocol is intentionally small. Animation, graphs, cost tracking and tool-level tracing are consumers/extensions of the same event stream, not replacements for it.