#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AgentHub: portable, dependency-free real-time multi-agent dashboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import uuid
import webbrowser
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
EVENT_FILE = "agenthub-events.jsonl"
USER = Path(os.environ.get("USERPROFILE") or Path.home())

DEFAULT_ROOTS = [
    BASE / "data" / "runs",
    USER / "Documents" / "CodePilot" / "TeamRuns",
]
CODEPILOT_UI_PATCHER = BASE / "adapters" / "codepilot" / "ensure_ui.py"

STATUS_BY_EVENT = {
    "agent.created": "created",
    "agent.routing": "routing",
    "agent.routed": "ready",
    "agent.started": "running",
    "agent.waiting": "waiting",
    "agent.blocked": "blocked",
    "agent.completed": "completed",
    "agent.failed": "failed",
}

RUN_STATUS_BY_EVENT = {
    "run.created": "running",
    "run.completed": "completed",
    "run.failed": "failed",
}

NON_FAILURE_AGENT_EVENTS = set(STATUS_BY_EVENT) - {"agent.failed"}
RUN_ACTIVE_AGENT_EVENTS = {"agent.routing", "agent.routed", "agent.started", "agent.waiting"}
RETRY_RESET_EVENTS = {"agent.routing", "agent.routed", "agent.started"}
ACTIVE_AGENT_STATUSES = {"created", "routing", "ready", "running", "waiting"}
WORKING_AGENT_STATUSES = {"routing", "ready", "running"}
ISSUE_AGENT_STATUSES = {"failed", "blocked", "timed_out", "stuck", "error"}


def configured_roots() -> list[Path]:
    raw = os.environ.get("AGENTHUB_RUN_ROOTS", "").strip()
    roots = [Path(x).expanduser() for x in raw.split(os.pathsep) if x.strip()] if raw else DEFAULT_ROOTS
    seen = set()
    result = []
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key not in seen:
            seen.add(key)
            result.append(root)
    return result


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.is_file():
        return out
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        out.append(item)
                except Exception:
                    pass
    except Exception:
        pass
    return out


def run_mtime(run_dir: Path) -> float:
    latest = 0.0
    try:
        latest = run_dir.stat().st_mtime
        for p in run_dir.rglob("*"):
            try:
                latest = max(latest, p.stat().st_mtime)
            except OSError:
                pass
    except OSError:
        pass
    return latest


def parse_legacy_summary(path: Path) -> dict[str, dict]:
    result = {}
    if not path.is_file():
        return result
    current = None
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if raw.startswith("## "):
            current = raw[3:].strip()
            result.setdefault(current, {})
        elif current and raw.startswith("- Status: "):
            result[current]["status"] = raw.split(":", 1)[1].strip()
        elif current and raw.startswith("- Model: "):
            result[current]["model"] = raw.split(":", 1)[1].strip()
        elif current and raw.startswith("- Error: "):
            result[current]["error"] = raw.split(":", 1)[1].strip()
    return result


def replay_standard(run_dir: Path, events: list[dict]) -> dict:
    state = {
        "run_id": run_dir.name,
        "title": run_dir.name,
        "status": "unknown",
        "status_since": "",
        "last_event_at": "",
        "workspace": "",
        "source": "",
        "agents": {},
        "events": events[-100:],
        "updated_at": run_mtime(run_dir),
        "path": str(run_dir),
        "protocol": "0.1",
    }
    for event in events:
        etype = str(event.get("type") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        event_ts = str(event.get("ts") or "")
        if event_ts:
            state["last_event_at"] = event_ts
        state["source"] = str(event.get("source") or state["source"])
        if etype in RUN_STATUS_BY_EVENT:
            next_run_status = RUN_STATUS_BY_EVENT[etype]
            if next_run_status != state["status"]:
                state["status_since"] = event_ts or state["status_since"]
            state["status"] = next_run_status
            state["title"] = str(data.get("title") or state["title"])
            state["workspace"] = str(data.get("workspace") or state["workspace"])
        elif etype in RUN_ACTIVE_AGENT_EVENTS:
            # A newer active-agent event re-opens the run after a stale terminal
            # event. This is important for retries/failover within the same run.
            if state["status"] != "running":
                state["status_since"] = event_ts or state["status_since"]
            state["status"] = "running"
        agent_id = event.get("agent_id")
        if not agent_id:
            continue
        agent_id = str(agent_id)
        agent = state["agents"].setdefault(agent_id, {
            "agent_id": agent_id,
            "name": agent_id,
            "role": "",
            "task": "",
            "model": "",
            "requested_model": "",
            "status": "unknown",
            "status_since": "",
            "message": "",
            "error": "",
            "elapsed_sec": None,
            "depends_on": [],
            "updated_at": "",
        })
        # Errors are point-in-time state, not permanent history. If a newer
        # non-failure lifecycle event arrives without an error, clear the stale
        # failure so retries/fallbacks do not keep rendering "execution error".
        if etype in NON_FAILURE_AGENT_EVENTS and "error" not in data:
            agent["error"] = ""
        if etype in RETRY_RESET_EVENTS:
            if "message" not in data:
                agent["message"] = ""
            if "elapsed_sec" not in data:
                agent["elapsed_sec"] = None

        for key in ("name", "role", "task", "model", "requested_model", "message", "error", "elapsed_sec", "depends_on"):
            if key in data and data[key] is not None:
                agent[key] = data[key]
        if etype in STATUS_BY_EVENT:
            next_agent_status = STATUS_BY_EVENT[etype]
            if next_agent_status != agent["status"]:
                agent["status_since"] = event_ts or agent["status_since"]
            agent["status"] = next_agent_status
        agent["updated_at"] = event_ts or agent["updated_at"]
    state["agents"] = list(state["agents"].values())
    return state


def legacy_state(run_dir: Path) -> dict:
    plan = read_json(run_dir / "plan.json", {}) or {}
    agents_plan = plan.get("agents") if isinstance(plan, dict) else []
    agents_plan = agents_plan if isinstance(agents_plan, list) else []
    summary = parse_legacy_summary(run_dir / "summary.md")
    summary_text = ""
    try:
        summary_text = (run_dir / "summary.md").read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        pass
    workspace = ""
    m = re.search(r"^- Source workspace:\s*(.+)$", summary_text, flags=re.M)
    if m:
        workspace = m.group(1).strip()

    agents = []
    for item in agents_plan:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "Agent")
        found = summary.get(name, {})
        status = found.get("status") or ("running" if not (run_dir / "summary.md").exists() else "unknown")
        model = found.get("model") or str(item.get("model") or "")
        final = ""
        agent_dir = None
        for child in run_dir.iterdir() if run_dir.exists() else []:
            if child.is_dir() and child.name.lower() == re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")[:48].lower():
                agent_dir = child
                break
        if agent_dir and (agent_dir / "final.txt").is_file():
            try:
                final = (agent_dir / "final.txt").read_text(encoding="utf-8-sig", errors="replace").strip()
            except Exception:
                pass
        agents.append({
            "agent_id": re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._").lower() or "agent",
            "name": name,
            "role": str(item.get("route_role") or ""),
            "task": str(item.get("prompt") or ""),
            "model": model,
            "requested_model": str(item.get("model") or ""),
            "status": status,
            "status_since": "",
            "message": final[-1000:],
            "error": str(found.get("error") or ""),
            "elapsed_sec": None,
            "depends_on": item.get("depends_on") if isinstance(item.get("depends_on"), list) else [],
            "updated_at": "",
        })
    run_status = "completed" if (run_dir / "summary.md").is_file() else "running"
    if any(a["status"] in {"failed", "timed_out"} for a in agents):
        run_status = "failed"
    return {
        "run_id": run_dir.name,
        "title": run_dir.name,
        "status": run_status,
        "status_since": "",
        "last_event_at": "",
        "workspace": workspace,
        "source": "legacy.team-orchestrator",
        "agents": agents,
        "events": [],
        "updated_at": run_mtime(run_dir),
        "path": str(run_dir),
        "protocol": "legacy",
    }


def current_state_metrics(state: dict) -> dict:
    agents = state.get("agents") if isinstance(state.get("agents"), list) else []
    statuses = [str(a.get("status") or "unknown").lower() for a in agents if isinstance(a, dict)]
    issue_agents = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        status = str(agent.get("status") or "unknown").lower()
        error = str(agent.get("error") or "").strip()
        unresolved_error = bool(error) and status not in ACTIVE_AGENT_STATUSES and status != "completed"
        if status in ISSUE_AGENT_STATUSES or unresolved_error:
            issue_agents.append(str(agent.get("agent_id") or agent.get("name") or "agent"))

    issue_count = len(issue_agents)
    run_status = str(state.get("status") or "unknown").lower()
    if run_status in {"failed", "error"} and issue_count == 0:
        issue_count = 1

    return {
        "agent_count": len(agents),
        "active_count": sum(s in ACTIVE_AGENT_STATUSES for s in statuses),
        "working_count": sum(s in WORKING_AGENT_STATUSES for s in statuses),
        "waiting_count": sum(s == "waiting" for s in statuses),
        "completed_count": sum(s == "completed" for s in statuses),
        "blocked_count": sum(s in {"blocked", "stuck"} for s in statuses),
        "failed_count": sum(s in {"failed", "timed_out", "error"} for s in statuses),
        "issue_count": issue_count,
        "issue_agents": issue_agents,
        "last_activity_at": state.get("last_event_at") or state.get("updated_at"),
    }


def load_run(run_dir: Path) -> dict:
    events = read_jsonl(run_dir / EVENT_FILE)
    state = replay_standard(run_dir, events) if events else legacy_state(run_dir)
    state["metrics"] = current_state_metrics(state)
    return state


def all_run_dirs() -> list[Path]:
    found = {}
    for root in configured_roots():
        if not root.is_dir():
            continue
        try:
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                if not ((child / EVENT_FILE).is_file() or (child / "plan.json").is_file() or (child / "summary.md").is_file()):
                    continue
                key = child.name
                existing = found.get(key)
                if existing is None or run_mtime(child) > run_mtime(existing):
                    found[key] = child
        except OSError:
            pass
    return sorted(found.values(), key=run_mtime, reverse=True)


def find_run(run_id: str) -> Path | None:
    for run_dir in all_run_dirs():
        if run_dir.name == run_id:
            return run_dir
    return None


def list_runs() -> list[dict]:
    out = []
    for run_dir in all_run_dirs()[:100]:
        state = load_run(run_dir)
        out.append({
            "run_id": state["run_id"],
            "title": state["title"],
            "status": state["status"],
            "source": state["source"],
            "agent_count": len(state["agents"]),
            "active_count": state["metrics"]["active_count"],
            "issue_count": state["metrics"]["issue_count"],
            "updated_at": state["updated_at"],
            "protocol": state["protocol"],
        })
    return out


def snapshot(run_id: str | None) -> dict:
    runs = all_run_dirs()
    run_dir = find_run(run_id) if run_id else (runs[0] if runs else None)
    if not run_dir:
        return {
            "run_id": "", "title": "暂无团队任务", "status": "idle", "status_since": "",
            "last_event_at": "", "workspace": "", "source": "", "agents": [], "events": [],
            "updated_at": time.time(), "protocol": "0.1",
            "metrics": {
                "agent_count": 0, "active_count": 0, "working_count": 0, "waiting_count": 0,
                "completed_count": 0, "blocked_count": 0, "failed_count": 0, "issue_count": 0,
                "issue_agents": [], "last_activity_at": time.time(),
            },
        }
    return load_run(run_dir)


def codepilot_ui_selfheal_loop(interval: int = 30) -> None:
    while True:
        if CODEPILOT_UI_PATCHER.is_file():
            try:
                subprocess.run(
                    [sys.executable, str(CODEPILOT_UI_PATCHER), "--quiet"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                pass
        time.sleep(max(15, interval))


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentHub/0.1"

    def log_message(self, fmt, *args):
        return

    def send_json(self, obj, status=200):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            return self.send_json({"ok": True, "version": "0.1", "roots": [str(x) for x in configured_roots()]})

        if path == "/api/runs":
            return self.send_json({"runs": list_runs()})

        if path.startswith("/api/run/"):
            run_id = urllib.parse.unquote(path[len("/api/run/"):])
            run_dir = find_run(run_id)
            return self.send_json(load_run(run_dir) if run_dir else {"error": "run not found"}, 200 if run_dir else 404)

        if path == "/api/stream":
            run_id = (query.get("run_id") or [""])[0] or None
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            last_hash = ""
            try:
                while True:
                    data = snapshot(run_id)
                    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
                    if digest != last_hash:
                        payload = ("event: snapshot\ndata: " + raw + "\n\n").encode("utf-8")
                        self.wfile.write(payload)
                        self.wfile.flush()
                        last_hash = digest
                    else:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    time.sleep(1.0)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            return

        if path in {"/", "/index.html"}:
            file = WEB / "index.html"
            if not file.is_file():
                return self.send_json({"error": "web/index.html missing"}, 500)
            raw = file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)
            return

        return self.send_json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="AgentHub portable real-time dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    threading.Thread(target=codepilot_ui_selfheal_loop, name="agenthub-codepilot-selfheal", daemon=True).start()
    url = f"http://{args.host}:{args.port}/"
    print(f"AgentHub 0.1 listening on {url}", flush=True)
    print("Run roots:", flush=True)
    for root in configured_roots():
        print(" -", root, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()