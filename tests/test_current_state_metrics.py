#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agenthub_server", BASE / "server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def event(kind: str, ts: str, *, agent_id: str | None = None, data: dict | None = None):
    item = {
        "version": "0.1",
        "id": "evt-" + kind,
        "ts": ts,
        "type": kind,
        "run_id": "metrics-test",
        "source": "test",
        "data": data or {},
    }
    if agent_id:
        item["agent_id"] = agent_id
    return item


with tempfile.TemporaryDirectory() as td:
    run_dir = Path(td) / "metrics-test"
    run_dir.mkdir()

    state = server.replay_standard(run_dir, [
        event("run.created", "2026-09-22T02:00:00+08:00", data={"title": "Metrics"}),
        event("agent.created", "2026-09-22T02:00:01+08:00", agent_id="frontend", data={"name": "Frontend"}),
        event("agent.started", "2026-09-22T02:00:02+08:00", agent_id="frontend", data={"model": "model-a"}),
        event("agent.created", "2026-09-22T02:00:03+08:00", agent_id="tester", data={"name": "Tester"}),
        event("agent.blocked", "2026-09-22T02:00:04+08:00", agent_id="tester", data={"error": "waiting for fixture"}),
        event("agent.created", "2026-09-22T02:00:05+08:00", agent_id="reviewer", data={"name": "Reviewer"}),
        event("agent.completed", "2026-09-22T02:00:06+08:00", agent_id="reviewer", data={"message": "done"}),
    ])

    metrics = server.current_state_metrics(state)
    assert metrics["agent_count"] == 3, metrics
    assert metrics["active_count"] == 1, metrics
    assert metrics["working_count"] == 1, metrics
    assert metrics["completed_count"] == 1, metrics
    assert metrics["blocked_count"] == 1, metrics
    assert metrics["failed_count"] == 0, metrics
    assert metrics["issue_count"] == 1, metrics
    assert metrics["issue_agents"] == ["tester"], metrics
    assert state["last_event_at"] == "2026-09-22T02:00:06+08:00", state
    frontend = next(a for a in state["agents"] if a["agent_id"] == "frontend")
    assert frontend["status"] == "running", frontend
    assert frontend["status_since"] == "2026-09-22T02:00:02+08:00", frontend

    recovered = server.replay_standard(run_dir, [
        event("run.created", "2026-09-22T02:10:00+08:00"),
        event("agent.failed", "2026-09-22T02:10:01+08:00", agent_id="worker", data={"error": "temporary"}),
        event("agent.started", "2026-09-22T02:10:02+08:00", agent_id="worker", data={"model": "fallback"}),
        event("agent.completed", "2026-09-22T02:10:03+08:00", agent_id="worker", data={"message": "ok"}),
        event("run.completed", "2026-09-22T02:10:04+08:00"),
    ])
    recovered_metrics = server.current_state_metrics(recovered)
    assert recovered_metrics["issue_count"] == 0, recovered_metrics
    assert recovered_metrics["completed_count"] == 1, recovered_metrics

    run_only_failure = server.replay_standard(run_dir, [
        event("run.created", "2026-09-22T02:20:00+08:00"),
        event("run.failed", "2026-09-22T02:20:01+08:00"),
    ])
    run_only_metrics = server.current_state_metrics(run_only_failure)
    assert run_only_metrics["issue_count"] == 1, run_only_metrics

print("PASS: current state metrics reflect only unresolved issues and expose status timing")
