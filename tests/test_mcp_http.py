from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SERVER = ROOT / "agenthub" / "mcp_server.py"
PORT = 8877

from mcp import Client


async def connect_with_retry():
    url = f"http://127.0.0.1:{PORT}/mcp"
    last = None
    for _ in range(30):
        try:
            client = Client(url)
            await client.__aenter__()
            return client
        except Exception as exc:
            last = exc
            await asyncio.sleep(0.2)
    raise RuntimeError(f"HTTP MCP did not become ready: {last}")


async def main() -> None:
    proc = subprocess.Popen(
        [str(PYTHON), str(SERVER), "--transport", "streamable-http", "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client = None
    try:
        client = await connect_with_retry()
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        if "create_run" not in names or "get_run" not in names:
            raise SystemExit("FAIL HTTP MCP tools")
        created = await client.call_tool("create_run", {"title": "HTTP MCP test", "source": "test.http"})
        payload = created.structured_content or {}
        if not payload.get("run_id"):
            raise SystemExit("FAIL HTTP MCP create_run")
        print("PASS HTTP")
        print("protocol_version=" + str(client.protocol_version))
        print("tools=" + str(len(names)))
    finally:
        if client is not None:
            await client.__aexit__(None, None, None)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
