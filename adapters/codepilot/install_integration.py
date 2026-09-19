#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install or remove the AgentHub integration for CodePilot on Windows."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import winreg

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
SERVER = BASE / "server.py"
EVENT_ADAPTER = HERE / "install_adapter.py"
UI_PATCHER = HERE / "ensure_ui.py"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "AgentHub"


def pythonw_path() -> Path:
    current = Path(sys.executable).resolve()
    candidate = current.with_name("pythonw.exe")
    return candidate if candidate.is_file() else current


def run_script(path: Path, *args: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(path), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"{path.name} failed").strip())


def set_autostart() -> str:
    command = f'"{pythonw_path()}" "{SERVER}" --port 8765'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command)
    return command


def remove_autostart() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE)
    except FileNotFoundError:
        pass


def read_autostart() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return str(winreg.QueryValueEx(key, RUN_VALUE)[0])
    except FileNotFoundError:
        return ""


def server_ok() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            return bool(data.get("ok"))
    except Exception:
        return False


def start_server() -> None:
    if server_ok():
        return
    flags = 0
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        [str(pythonw_path()), str(SERVER), "--port", "8765"],
        cwd=str(BASE),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    deadline = time.time() + 8
    while time.time() < deadline:
        if server_ok():
            return
        time.sleep(0.25)
    raise RuntimeError("AgentHub server did not start on port 8765")


def install() -> None:
    run_script(EVENT_ADAPTER)
    run_script(UI_PATCHER)
    command = set_autostart()
    start_server()
    print("AgentHub CodePilot integration installed.")
    print("Autostart:", command)
    print("UI: CodePilot -> AI团队")


def uninstall() -> None:
    remove_autostart()
    run_script(UI_PATCHER, "--uninstall")
    run_script(EVENT_ADAPTER, "--uninstall")
    print("AgentHub CodePilot integration removed.")
    print("The currently running AgentHub background process, if any, stops on the next Windows sign-out/restart.")


def verify() -> int:
    checks = {
        "server": server_ok(),
        "autostart": bool(read_autostart()),
    }
    ui = subprocess.run(
        [sys.executable, str(UI_PATCHER), "--verify"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    checks["ui_patch"] = ui.returncode == 0
    target = Path.home() / ".codex" / "skills" / "team-orchestrator" / "scripts" / "team_fanout.py"
    try:
        checks["event_adapter"] = "AGENTHUB_ADAPTER_V01" in target.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        checks["event_adapter"] = False
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


def main() -> int:
    if os.name != "nt":
        print("This installer currently supports Windows only.", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--uninstall", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    try:
        if args.verify:
            return verify()
        if args.uninstall:
            uninstall()
        else:
            install()
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())