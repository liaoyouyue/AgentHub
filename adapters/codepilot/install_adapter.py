#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install/remove the AgentHub v0.1 event adapter for CodePilot team-orchestrator."""

from __future__ import annotations

import argparse
from pathlib import Path
import py_compile
import shutil
import sys
import time

USER = Path.home()
TARGET = USER / ".codex" / "skills" / "team-orchestrator" / "scripts" / "team_fanout.py"
BACKUP = TARGET.with_name("team_fanout.py.agenthub-pre-v01.bak")
MARKER = "# AGENTHUB_ADAPTER_V01"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


def install() -> None:
    if not TARGET.is_file():
        raise RuntimeError(f"target missing: {TARGET}")

    original = TARGET.read_text(encoding="utf-8-sig")
    if MARKER in original:
        print("AgentHub adapter already installed.")
        return

    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)

    text = original

    text = replace_once(
        text,
        '    slug = slugify(name)\n    sandbox = str(agent.get("sandbox") or "read-only")\n',
        '    slug = slugify(name)\n    event_agent_id = slug.lower()\n    sandbox = str(agent.get("sandbox") or "read-only")\n',
        "stable event agent id",
    )

    text = replace_once(
        text,
        "import tempfile\nimport time\nimport uuid\n",
        "import tempfile\nimport time\nimport uuid\nimport threading\nfrom datetime import datetime\n",
        "imports",
    )

    text = replace_once(
        text,
        '''def parse_jsonl(raw: str) -> dict:
    final_messages = []
    usage = None
    events = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        events += 1
        if obj.get("type") == "item.completed":
            item = obj.get("item") or {}
            if item.get("type") == "agent_message":
                final_messages.append(item.get("text", ""))
        if obj.get("type") == "turn.completed":
            usage = obj.get("usage")
    return {
        "events": events,
        "last_agent_message": final_messages[-1] if final_messages else "",
        "usage": usage,
    }
''',
        '''def parse_jsonl(raw: str) -> dict:
    final_messages = []
    errors = []
    usage = None
    events = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        events += 1
        if obj.get("type") == "item.completed":
            item = obj.get("item") or {}
            if item.get("type") == "agent_message":
                final_messages.append(item.get("text", ""))
            if item.get("type") == "error" and item.get("message"):
                errors.append(str(item.get("message")))
        if obj.get("type") == "error" and obj.get("message"):
            errors.append(str(obj.get("message")))
        if obj.get("type") == "turn.failed":
            failure = obj.get("error") or {}
            if isinstance(failure, dict) and failure.get("message"):
                errors.append(str(failure.get("message")))
        if obj.get("type") == "turn.completed":
            usage = obj.get("usage")
    return {
        "events": events,
        "last_agent_message": final_messages[-1] if final_messages else "",
        "last_error": errors[-1] if errors else "",
        "usage": usage,
    }
''',
        "failure parsing",
    )

    text = replace_once(
        text,
        '''        result_status = "completed" if proc.returncode == 0 and not no_expected_change else "failed"
        result_error = None
        if no_expected_change:
            result_error = "NO_WORKSPACE_CHANGES: write worker finished without producing a diff."
''',
        '''        result_status = "completed" if proc.returncode == 0 and not no_expected_change else "failed"
        result_error = None
        if no_expected_change:
            result_error = "NO_WORKSPACE_CHANGES: write worker finished without producing a diff."
        elif proc.returncode != 0:
            result_error = (
                parsed.get("last_error")
                or (proc.stderr or "").strip()[-1200:]
                or "Child process exited with code {}".format(proc.returncode)
            )
''',
        "failure propagation",
    )

    helper = r'''
# AGENTHUB_ADAPTER_V01
AGENTHUB_EVENT_FILE = "agenthub-events.jsonl"
AGENTHUB_EVENT_LOCK = threading.Lock()

def emit_agenthub_event(run_dir: Path, run_id: str, event_type: str, *, agent_id=None, data=None):
    """Append one AgentHub protocol v0.1 event. Failure must never break the agent run."""
    try:
        event = {
            "version": "0.1",
            "id": "evt_" + uuid.uuid4().hex,
            "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "type": str(event_type),
            "run_id": str(run_id),
            "source": "codepilot.team-orchestrator",
            "data": data if isinstance(data, dict) else {},
        }
        if agent_id:
            event["agent_id"] = str(agent_id)
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        with AGENTHUB_EVENT_LOCK:
            with (run_dir / AGENTHUB_EVENT_FILE).open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
    except Exception:
        pass

'''
    text = replace_once(
        text,
        'SMART_ROUTER_CLI = USERPROFILE / ".codepilot" / "smart-router" / "route-cli.js"\n\ndef slugify',
        'SMART_ROUTER_CLI = USERPROFILE / ".codepilot" / "smart-router" / "route-cli.js"\n\n' + helper + 'def slugify',
        "event helper",
    )

    text = replace_once(
        text,
        '        resolved_model, router_route = resolve_agent_model(agent, node)\n        routed_agent = dict(agent)\n',
        '''        emit_agenthub_event(
            run_dir, run_id, "agent.routing", agent_id=event_agent_id,
            data={
                "name": name,
                "role": str(agent.get("route_role") or ""),
                "task": prompt,
                "requested_model": str(agent.get("model") or "auto"),
                "status": "routing",
            },
        )
        resolved_model, router_route = resolve_agent_model(agent, node)
        emit_agenthub_event(
            run_dir, run_id, "agent.routed", agent_id=event_agent_id,
            data={
                "name": name,
                "model": resolved_model,
                "requested_model": str(agent.get("model") or "auto"),
                "status": "ready",
            },
        )
        routed_agent = dict(agent)
''',
        "routing events",
    )

    text = replace_once(
        text,
        '        started = time.time()\n        proc = run_process(\n',
        '''        emit_agenthub_event(
            run_dir, run_id, "agent.started", agent_id=event_agent_id,
            data={
                "name": name,
                "role": str(agent.get("route_role") or ""),
                "task": prompt,
                "model": resolved_model,
                "requested_model": str(agent.get("model") or "auto"),
                "status": "running",
            },
        )
        started = time.time()
        proc = run_process(
''',
        "started event",
    )

    text = replace_once(
        text,
        '    (run_dir / "plan.json").write_text(json.dumps({"agents": agents}, ensure_ascii=False, indent=2), encoding="utf-8")\n\n    env = dict(os.environ)\n',
        '''    (run_dir / "plan.json").write_text(json.dumps({"agents": agents}, ensure_ascii=False, indent=2), encoding="utf-8")

    emit_agenthub_event(
        run_dir, run_id, "run.created",
        data={
            "title": str(plan.get("title") or cwd.name) if isinstance(plan, dict) else cwd.name,
            "workspace": str(cwd),
            "status": "running",
        },
    )
    for agent in agents:
        name = str(agent.get("name") or "Agent")
        emit_agenthub_event(
            run_dir, run_id, "agent.created", agent_id=slugify(name).lower(),
            data={
                "name": name,
                "role": str(agent.get("route_role") or ""),
                "task": str(agent.get("prompt") or ""),
                "requested_model": str(agent.get("model") or "auto"),
                "status": "created",
                "depends_on": agent.get("depends_on") if isinstance(agent.get("depends_on"), list) else [],
            },
        )

    env = dict(os.environ)
''',
        "run created events",
    )

    old_pool = '''        for future in futures:
            results.append(future.result())

    summary = run_dir / "summary.md"
'''
    new_pool = '''        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            agent_slug = slugify(str(result.get("name") or "Agent")).lower()
            success = result.get("status") == "completed"
            emit_agenthub_event(
                run_dir, run_id, "agent.completed" if success else "agent.failed",
                agent_id=agent_slug,
                data={
                    "name": str(result.get("name") or "Agent"),
                    "status": result.get("status"),
                    "model": result.get("model"),
                    "requested_model": result.get("requested_model"),
                    "elapsed_sec": result.get("elapsed_sec"),
                    "message": str(result.get("final_text") or "")[-2000:],
                    "error": str(result.get("error") or ""),
                },
            )

    summary = run_dir / "summary.md"
'''
    text = replace_once(text, old_pool, new_pool, "completion events")

    text = replace_once(
        text,
        '    print(json.dumps(output, ensure_ascii=False, indent=2))\n    return 0 if all(r.get("status") == "completed" for r in results) else 2\n',
        '''    all_ok = all(r.get("status") == "completed" for r in results)
    emit_agenthub_event(
        run_dir, run_id, "run.completed" if all_ok else "run.failed",
        data={
            "title": str(plan.get("title") or cwd.name) if isinstance(plan, dict) else cwd.name,
            "workspace": str(cwd),
            "status": "completed" if all_ok else "failed",
        },
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if all_ok else 2
''',
        "run completion",
    )

    temp = TARGET.with_suffix(".py.agenthub.tmp")
    temp.write_text(text, encoding="utf-8")
    try:
        py_compile.compile(str(temp), doraise=True)
        shutil.copy2(temp, TARGET)
        py_compile.compile(str(TARGET), doraise=True)
    except Exception:
        if BACKUP.exists():
            shutil.copy2(BACKUP, TARGET)
        raise
    finally:
        temp.unlink(missing_ok=True)

    print(f"Installed AgentHub adapter into: {TARGET}")
    print(f"Rollback backup: {BACKUP}")


def uninstall() -> None:
    if not BACKUP.is_file():
        raise RuntimeError(f"backup missing: {BACKUP}")
    shutil.copy2(BACKUP, TARGET)
    py_compile.compile(str(TARGET), doraise=True)
    print("AgentHub adapter removed and original team_fanout.py restored.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()
    try:
        uninstall() if args.uninstall else install()
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())