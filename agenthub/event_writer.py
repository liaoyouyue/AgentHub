from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = ROOT / "data" / "runs"
_LOCK = threading.Lock()


def runs_root() -> Path:
    raw = os.environ.get("AGENTHUB_RUN_DIR", "").strip()
    root = Path(raw).expanduser() if raw else DEFAULT_RUNS
    root.mkdir(parents=True, exist_ok=True)
    return root


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._").lower()
    return slug[:64] or "agent"


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def event_path(run_id: str) -> Path:
    run_dir = runs_root() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / "agenthub-events.jsonl"


def emit(
    run_id: str,
    event_type: str,
    *,
    source: str = "agenthub.generic",
    agent_id: str | None = None,
    data: dict[str, Any] | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "version": "0.1",
        "id": "evt_" + uuid.uuid4().hex,
        "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "type": str(event_type),
        "run_id": str(run_id),
        "source": str(source),
        "data": data if isinstance(data, dict) else {},
    }
    if agent_id:
        event["agent_id"] = slugify(agent_id)
    if trace_id:
        event["trace_id"] = trace_id
    if span_id:
        event["span_id"] = span_id
    if parent_span_id:
        event["parent_span_id"] = parent_span_id

    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    path = event_path(run_id)
    with _LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
    return event


def create_run(title: str, workspace: str = "", source: str = "agenthub.generic") -> str:
    run_id = new_run_id()
    emit(
        run_id,
        "run.created",
        source=source,
        data={"title": title or run_id, "workspace": workspace, "status": "running"},
    )
    return run_id


def create_agent(
    run_id: str,
    agent_id: str,
    *,
    name: str = "",
    role: str = "",
    task: str = "",
    model: str = "",
    requested_model: str = "",
    depends_on: list[str] | None = None,
    source: str = "agenthub.generic",
) -> dict[str, Any]:
    aid = slugify(agent_id)
    return emit(
        run_id,
        "agent.created",
        source=source,
        agent_id=aid,
        data={
            "name": name or agent_id,
            "role": role,
            "task": task,
            "model": model,
            "requested_model": requested_model,
            "depends_on": [slugify(x) for x in (depends_on or [])],
            "status": "created",
        },
    )


def update_agent(
    run_id: str,
    agent_id: str,
    status: str,
    *,
    name: str = "",
    role: str = "",
    task: str = "",
    model: str = "",
    requested_model: str = "",
    message: str = "",
    error: str = "",
    elapsed_sec: float | None = None,
    depends_on: list[str] | None = None,
    source: str = "agenthub.generic",
) -> dict[str, Any]:
    mapping = {
        "created": "agent.created",
        "routing": "agent.routing",
        "ready": "agent.routed",
        "running": "agent.started",
        "waiting": "agent.waiting",
        "blocked": "agent.blocked",
        "completed": "agent.completed",
        "failed": "agent.failed",
    }
    event_type = mapping.get(status, "agent.message")
    data: dict[str, Any] = {"status": status}
    for key, value in {
        "name": name,
        "role": role,
        "task": task,
        "model": model,
        "requested_model": requested_model,
        "message": message,
        "error": error,
        "elapsed_sec": elapsed_sec,
        "depends_on": [slugify(x) for x in (depends_on or [])] if depends_on is not None else None,
    }.items():
        if value not in ("", None, []):
            data[key] = value
    return emit(run_id, event_type, source=source, agent_id=agent_id, data=data)


def complete_run(
    run_id: str,
    *,
    success: bool = True,
    title: str = "",
    workspace: str = "",
    message: str = "",
    source: str = "agenthub.generic",
) -> dict[str, Any]:
    return emit(
        run_id,
        "run.completed" if success else "run.failed",
        source=source,
        data={
            "title": title,
            "workspace": workspace,
            "message": message,
            "status": "completed" if success else "failed",
        },
    )
