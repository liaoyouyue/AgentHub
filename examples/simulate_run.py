#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import time
import uuid

BASE = Path(__file__).resolve().parents[1]
RUN_ID = "demo-" + datetime.now().strftime("%Y%m%d-%H%M%S")
RUN_DIR = BASE / "data" / "runs" / RUN_ID
EVENTS = RUN_DIR / "agenthub-events.jsonl"


def emit(event_type, agent_id=None, **data):
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "version": "0.1",
        "id": "evt_" + uuid.uuid4().hex,
        "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "type": event_type,
        "run_id": RUN_ID,
        "source": "agenthub.demo",
        "data": data,
    }
    if agent_id:
        event["agent_id"] = agent_id
    with EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        fh.flush()


def main():
    emit("run.created", title="AgentHub 实时同步演示", workspace=str(BASE), status="running")

    agents = [
        ("architect", "Architect", "deep", "分析任务和依赖"),
        ("backend", "Backend", "normal", "实现数据接口"),
        ("qa", "QA", "fast", "等待后端完成后验证"),
    ]
    for aid, name, role, task in agents:
        emit("agent.created", aid, name=name, role=role, task=task, requested_model="auto", status="created")

    time.sleep(1)
    emit("agent.routing", "architect", name="Architect", status="routing")
    time.sleep(1)
    emit("agent.routed", "architect", name="Architect", model="deep-model", status="ready")
    emit("agent.started", "architect", name="Architect", model="deep-model", task="分析任务和依赖", status="running")
    time.sleep(2)
    emit("agent.completed", "architect", name="Architect", model="deep-model", elapsed_sec=4.0, message="架构分析完成", status="completed")

    emit("agent.routed", "backend", name="Backend", model="coding-model", status="ready")
    emit("agent.started", "backend", name="Backend", model="coding-model", task="实现数据接口", status="running")
    emit("agent.waiting", "qa", name="QA", task="等待 Backend", depends_on=["backend"], status="waiting")
    time.sleep(2)
    emit("agent.completed", "backend", name="Backend", model="coding-model", elapsed_sec=2.0, message="接口实现完成", status="completed")

    emit("agent.routed", "qa", name="QA", model="fast-model", status="ready")
    emit("agent.started", "qa", name="QA", model="fast-model", task="验证实时状态", status="running")
    time.sleep(2)
    emit("agent.completed", "qa", name="QA", model="fast-model", elapsed_sec=2.0, message="实时同步验证通过", status="completed")

    emit("run.completed", title="AgentHub 实时同步演示", workspace=str(BASE), status="completed")
    print(RUN_ID)


if __name__ == "__main__":
    main()