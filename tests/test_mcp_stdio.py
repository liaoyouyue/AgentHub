from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SERVER = ROOT / "agenthub" / "mcp_server.py"

from mcp import Client, StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
    )
    async with Client(params) as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        if "create_run" not in names or "update_agent" not in names:
            raise SystemExit("FAIL stdio tools")
        created = await client.call_tool("create_run", {"title": "STDIO host test", "source": "test.stdio"})
        payload = created.structured_content or {}
        if not payload.get("run_id"):
            raise SystemExit("FAIL stdio create_run")
        print("PASS STDIO")
        print("protocol_version=" + str(client.protocol_version))
        print("tools=" + str(len(names)))


if __name__ == "__main__":
    asyncio.run(main())
