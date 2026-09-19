#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agenthub.event_writer import complete_run, create_agent, create_run, emit, update_agent


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Wrap any command/agent process and publish its lifecycle to AgentHub."
    )
    ap.add_argument("--title", default="Generic Agent Task")
    ap.add_argument("--agent", default="worker")
    ap.add_argument("--name", default="")
    ap.add_argument("--role", default="")
    ap.add_argument("--task", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--workspace", default=os.getcwd())
    ap.add_argument("--source", default="generic.command")
    ap.add_argument("--run-id", default="", help="Join an existing AgentHub run instead of creating one.")
    ap.add_argument("--no-stream", action="store_true", help="Do not emit stdout/stderr lines as agent.message events.")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        ap.error("a command is required after --")

    owns_run = not bool(args.run_id)
    run_id = args.run_id or create_run(args.title, args.workspace, args.source)
    agent_name = args.name or args.agent

    create_agent(
        run_id,
        args.agent,
        name=agent_name,
        role=args.role,
        task=args.task or " ".join(command),
        model=args.model,
        source=args.source,
    )
    update_agent(
        run_id,
        args.agent,
        "running",
        name=agent_name,
        role=args.role,
        task=args.task or " ".join(command),
        model=args.model,
        source=args.source,
    )

    started = time.time()
    proc = subprocess.Popen(
        command,
        cwd=args.workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    collected: list[str] = []
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip("\r\n")
        print(line, flush=True)
        if line:
            collected.append(line)
            if len(collected) > 100:
                collected = collected[-100:]
            if not args.no_stream:
                emit(
                    run_id,
                    "agent.message",
                    source=args.source,
                    agent_id=args.agent,
                    data={"name": agent_name, "message": line, "status": "running"},
                )

    rc = proc.wait()
    elapsed = round(time.time() - started, 3)
    tail = "\n".join(collected[-20:])[-4000:]

    if rc == 0:
        update_agent(
            run_id,
            args.agent,
            "completed",
            name=agent_name,
            model=args.model,
            message=tail,
            elapsed_sec=elapsed,
            source=args.source,
        )
    else:
        error = tail or f"Command exited with code {rc}"
        update_agent(
            run_id,
            args.agent,
            "failed",
            name=agent_name,
            model=args.model,
            error=error,
            message=tail,
            elapsed_sec=elapsed,
            source=args.source,
        )

    if owns_run:
        complete_run(
            run_id,
            success=(rc == 0),
            title=args.title,
            workspace=args.workspace,
            message=f"Command exit code: {rc}",
            source=args.source,
        )

    print(f"[AgentHub] run_id={run_id} exit_code={rc}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
