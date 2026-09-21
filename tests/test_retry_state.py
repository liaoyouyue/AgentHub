#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agenthub_server", BASE / "server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def event(kind: str, *, agent_id: str | None = None, data: dict | None = None):
    item = {
        "version": "0.1",
        "id": "evt-test",
        "ts": "2026-09-22T02:00:00+08:00",
        "type": kind,
        "run_id": "retry-test",
        "source": "test",
        "data": data or {},
    }
    if agent_id:
        item["agent_id"] = agent_id
    return item


with tempfile.TemporaryDirectory() as td:
    run_dir = Path(td) / "retry-test"
    run_dir.mkdir()

    state = server.replay_standard(run_dir, [
        event("run.created", data={"title": "Retry test", "status": "running"}),
        event("agent.created", agent_id="worker", data={"name": "Worker"}),
        event("agent.failed", agent_id="worker", data={"error": "usage limit", "status": "failed"}),
        event("agent.routing", agent_id="worker", data={"status": "routing"}),
        event("agent.started", agent_id="worker", data={"status": "running", "model": "fallback-model"}),
        event("agent.completed", agent_id="worker", data={"status": "completed", "message": "ok"}),
        event("run.completed", data={"status": "completed"}),
    ])

    worker = state["agents"][0]
    assert state["status"] == "completed", state
    assert worker["status"] == "completed", worker
    assert worker["error"] == "", worker
    assert worker["message"] == "ok", worker

    reopened = server.replay_standard(run_dir, [
        event("run.created"),
        event("agent.failed", agent_id="worker", data={"error": "temporary failure"}),
        event("run.failed"),
        event("agent.started", agent_id="worker", data={"status": "running"}),
    ])
    assert reopened["status"] == "running", reopened
    assert reopened["agents"][0]["error"] == "", reopened["agents"][0]

    current_failure = server.replay_standard(run_dir, [
        event("run.created"),
        event("agent.failed", agent_id="worker", data={"error": "real failure"}),
        event("run.failed"),
    ])
    assert current_failure["status"] == "failed", current_failure
    assert current_failure["agents"][0]["error"] == "real failure", current_failure["agents"][0]

print("PASS: retry/failover state clears stale errors without hiding current failures")
