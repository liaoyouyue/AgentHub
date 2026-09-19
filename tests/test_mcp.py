from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp import Client
from agenthub.mcp_server import mcp


def result_payload(result):
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                pass
    return {}


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        required = {"create_run", "create_agent", "update_agent", "complete_run", "get_run", "list_runs"}
        missing = required - names
        if missing:
            raise SystemExit("FAIL missing tools: " + ", ".join(sorted(missing)))

        created = result_payload(await client.call_tool("create_run", {"title": "MCP portability test", "source": "test.mcp"}))
        run_id = created.get("run_id")
        if not run_id:
            raise SystemExit("FAIL no run_id")

        await client.call_tool("create_agent", {
            "run_id": run_id,
            "agent_id": "portable-worker",
            "name": "Portable Worker",
            "role": "test",
            "task": "Verify MCP host interoperability",
            "model": "test-model",
            "source": "test.mcp",
        })
        await client.call_tool("update_agent", {
            "run_id": run_id,
            "agent_id": "portable-worker",
            "status": "running",
            "message": "MCP tool call is live",
            "source": "test.mcp",
        })
        state = result_payload(await client.call_tool("get_run", {"run_id": run_id}))
        agents = state.get("agents") or []
        if not agents or agents[0].get("status") != "running":
            raise SystemExit("FAIL live agent state")

        await client.call_tool("update_agent", {
            "run_id": run_id,
            "agent_id": "portable-worker",
            "status": "completed",
            "message": "MCP portability test passed",
            "source": "test.mcp",
        })
        await client.call_tool("complete_run", {"run_id": run_id, "success": True, "source": "test.mcp"})
        final = result_payload(await client.call_tool("get_run", {"run_id": run_id}))
        if final.get("status") != "completed":
            raise SystemExit("FAIL final run state")

        print("PASS MCP")
        print("protocol_version=" + str(client.protocol_version))
        print("tools=" + str(len(names)))
        print("run_id=" + run_id)


if __name__ == "__main__":
    asyncio.run(main())
