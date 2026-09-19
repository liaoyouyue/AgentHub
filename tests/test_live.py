#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

BASE = Path(__file__).resolve().parents[1]
SIM = BASE / "examples" / "simulate_run.py"
API = "http://127.0.0.1:8765"


def get_json(url):
    with urllib.request.urlopen(url, timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    p = subprocess.Popen([sys.executable, str(SIM)], stdout=subprocess.PIPE, text=True)
    seen_live = False
    run_id = None
    deadline = time.time() + 12

    while time.time() < deadline and p.poll() is None:
        time.sleep(0.5)
        runs = get_json(API + "/api/runs").get("runs", [])
        demo = next((r for r in runs if str(r.get("run_id", "")).startswith("demo-")), None)
        if not demo:
            continue
        run_id = demo["run_id"]
        state = get_json(API + "/api/run/" + run_id)
        statuses = {a.get("status") for a in state.get("agents", [])}
        if state.get("status") == "running" and statuses.intersection({"running", "routing", "waiting", "created", "ready"}):
            seen_live = True
            break

    if not seen_live:
        p.terminate()
        raise SystemExit("FAIL: no live in-progress state observed")

    stdout, _ = p.communicate(timeout=12)
    final_id = (stdout or "").strip().splitlines()[-1]
    state = get_json(API + "/api/run/" + final_id)
    if state.get("status") != "completed":
        raise SystemExit("FAIL: final run did not complete")
    if not state.get("agents") or any(a.get("status") != "completed" for a in state["agents"]):
        raise SystemExit("FAIL: not all agents completed")

    print("PASS")
    print("run_id=" + final_id)
    print("live_state_seen=true")
    print("final_agents=" + str(len(state["agents"])))


if __name__ == "__main__":
    main()