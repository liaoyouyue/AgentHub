#!/usr/bin/env python3
from pathlib import Path
import importlib.util

TARGET = Path.home() / ".codex" / "skills" / "team-orchestrator" / "scripts" / "team_fanout.py"
spec = importlib.util.spec_from_file_location("team_fanout_agenthub_test", TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

raw = """{"type":"thread.started","thread_id":"test"}
{"type":"turn.started"}
{"type":"error","message":"Reconnecting... 2/5 (request timed out)"}
{"type":"item.completed","item":{"id":"item_0","type":"error","message":"Falling back transport"}}
{"type":"error","message":"You've hit your usage limit. Try again later."}
{"type":"turn.failed","error":{"message":"You've hit your usage limit. Try again later."}}
"""

parsed = mod.parse_jsonl(raw)
err = parsed.get("last_error") or ""
if "usage limit" not in err.lower():
    raise SystemExit("FAIL: usage-limit error was not extracted")
print("PASS: failure reason extracted")