from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server import MCPServer

import server as dashboard
from agenthub.event_writer import (
    complete_run as complete_run_event,
    create_agent as create_agent_event,
    create_run as create_run_event,
    emit,
    update_agent as update_agent_event,
)

INSTRUCTIONS = """AgentHub is a portable multi-agent observability/control bridge.
Use it to register real task and agent lifecycle state so the user can see work in real time.
Create one run for the overall task, create agents before they work, update status when routing,
running, waiting, blocked, completed or failed, and complete the run at the end.
Never invent progress percentages. Report only observed state and real messages/errors.
Do not include provider credentials, secrets, API keys or authentication tokens in events.
"""

mcp = MCPServer(
    "AgentHub",
    title="AgentHub",
    description="Portable real-time multi-agent visibility and lifecycle tools.",
    instructions=INSTRUCTIONS,
    version="0.2.0",
)


@mcp.tool(title="Create AgentHub run")
def create_run(title: str, workspace: str = "", source: str = "mcp.host") -> dict[str, str]:
    """Create a new AgentHub run and return its run_id."""
    run_id = create_run_event(title=title, workspace=workspace, source=source)
    return {"run_id": run_id, "status": "running"}


@mcp.tool(title="Create AgentHub agent")
def create_agent(
    run_id: str,
    agent_id: str,
    name: str = "",
    role: str = "",
    task: str = "",
    model: str = "",
    requested_model: str = "",
    depends_on: list[str] | None = None,
    source: str = "mcp.host",
) -> dict[str, Any]:
    """Register an agent inside a run before it begins work."""
    event = create_agent_event(
        run_id,
        agent_id,
        name=name,
        role=role,
        task=task,
        model=model,
        requested_model=requested_model,
        depends_on=depends_on,
        source=source,
    )
    return {"ok": True, "event": event}


@mcp.tool(title="Update AgentHub agent")
def update_agent(
    run_id: str,
    agent_id: str,
    status: str,
    name: str = "",
    role: str = "",
    task: str = "",
    model: str = "",
    requested_model: str = "",
    message: str = "",
    error: str = "",
    elapsed_sec: float | None = None,
    depends_on: list[str] | None = None,
    source: str = "mcp.host",
) -> dict[str, Any]:
    """Update an agent lifecycle state. Status: created/routing/ready/running/waiting/blocked/completed/failed."""
    allowed = {"created", "routing", "ready", "running", "waiting", "blocked", "completed", "failed"}
    if status not in allowed:
        raise ValueError("status must be one of: " + ", ".join(sorted(allowed)))
    event = update_agent_event(
        run_id,
        agent_id,
        status,
        name=name,
        role=role,
        task=task,
        model=model,
        requested_model=requested_model,
        message=message,
        error=error,
        elapsed_sec=elapsed_sec,
        depends_on=depends_on,
        source=source,
    )
    return {"ok": True, "event": event}


@mcp.tool(title="Emit AgentHub event")
def emit_event(
    run_id: str,
    event_type: str,
    agent_id: str = "",
    message: str = "",
    source: str = "mcp.host",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit a protocol event directly for adapters that already map their own lifecycle."""
    payload = dict(data or {})
    if message:
        payload["message"] = message
    event = emit(
        run_id,
        event_type,
        source=source,
        agent_id=agent_id or None,
        data=payload,
    )
    return {"ok": True, "event": event}


@mcp.tool(title="Complete AgentHub run")
def complete_run(
    run_id: str,
    success: bool = True,
    title: str = "",
    workspace: str = "",
    message: str = "",
    source: str = "mcp.host",
) -> dict[str, Any]:
    """Mark an AgentHub run completed or failed."""
    event = complete_run_event(
        run_id,
        success=success,
        title=title,
        workspace=workspace,
        message=message,
        source=source,
    )
    return {"ok": True, "event": event}


@mcp.tool(title="Get AgentHub run")
def get_run(run_id: str = "") -> dict[str, Any]:
    """Return reconstructed state for a run, or the latest run when run_id is empty."""
    if run_id:
        run_dir = dashboard.find_run(run_id)
        if not run_dir:
            return {"error": "run not found", "run_id": run_id}
        return dashboard.load_run(run_dir)
    return dashboard.snapshot(None)


@mcp.tool(title="List AgentHub runs")
def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """List recent AgentHub runs."""
    limit = max(1, min(int(limit), 100))
    return dashboard.list_runs()[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="AgentHub MCP server")
    ap.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8876)
    args = ap.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
