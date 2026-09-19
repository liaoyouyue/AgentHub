#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
VENV_DIR = ROOT / ".venv"
PYTHON = VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
SERVER = ROOT / "agenthub" / "mcp_server.py"
REQ = ROOT / "requirements-mcp.txt"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(cmd) if sys.platform == "win32" else " ".join(cmd))
    return subprocess.run(cmd, text=True, check=check)


def bootstrap() -> None:
    if not PYTHON.exists():
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    run([str(PYTHON), "-m", "pip", "install", "-r", str(REQ)])


def stdio_config() -> dict:
    return {
        "type": "stdio",
        "command": str(PYTHON),
        "args": [str(SERVER)],
    }


def cursor_install(dry_run: bool) -> None:
    path = Path.home() / ".cursor" / "mcp.json"
    cfg: dict = {}
    if path.is_file():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise RuntimeError(f"Cannot parse existing Cursor config: {path}: {exc}") from exc
    servers = cfg.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise RuntimeError("Cursor mcpServers is not an object")
    entry = stdio_config()
    entry.pop("type", None)
    servers["agenthub"] = entry
    if dry_run:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Installed AgentHub MCP into Cursor:", path)


def cli_install(host: str, dry_run: bool) -> None:
    exe = shutil.which(host)
    if not exe:
        if dry_run:
            exe = host
        else:
            raise RuntimeError(f"{host} command was not found in PATH")

    if host == "codex":
        cmd = [exe, "mcp", "add", "agenthub", "--", str(PYTHON), str(SERVER)]
    elif host == "claude":
        cmd = [exe, "mcp", "add", "agenthub", "--scope", "user", "--", str(PYTHON), str(SERVER)]
    elif host == "opencode":
        cmd = [exe, "mcp", "add", "agenthub", "--", str(PYTHON), str(SERVER)]
    else:
        raise ValueError(host)

    if dry_run:
        print(subprocess.list2cmdline(cmd) if sys.platform == "win32" else " ".join(cmd))
        return
    run(cmd)


def print_generic() -> None:
    print(json.dumps({"mcpServers": {"agenthub": stdio_config()}}, ensure_ascii=False, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap and connect AgentHub MCP to supported AI hosts.")
    ap.add_argument(
        "--host",
        choices=["codex", "claude", "cursor", "opencode", "generic", "none"],
        default="none",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-bootstrap", action="store_true")
    args = ap.parse_args()

    try:
        if not args.skip_bootstrap and not args.dry_run:
            bootstrap()

        if args.host == "none":
            print("AgentHub MCP runtime:", PYTHON)
            print("AgentHub MCP server:", SERVER)
            return 0
        if args.host == "generic":
            print_generic()
        elif args.host == "cursor":
            cursor_install(args.dry_run)
        else:
            cli_install(args.host, args.dry_run)
        return 0
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
