#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]
TARGET = BASE / "adapters" / "codepilot" / "ensure_ui.py"
SPEC = importlib.util.spec_from_file_location("agenthub_codepilot_ui", TARGET)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

assert mod.VERSION == "0.2.0", mod.VERSION
assert "V02" in mod.MARK, mod.MARK
assert "V01" in mod.LEGACY_MARK, mod.LEGACY_MARK

original = "console.log('codepilot original');\n"
legacy = original + ";" + mod.LEGACY_MARK + "\n(()=>{oldUi=true})();\n"
current = original + ";" + mod.MARK + "\n(()=>{newUi=true})();\n"
assert mod.strip_injected_ui(legacy) == original
assert mod.strip_injected_ui(current) == original
assert mod.strip_injected_ui(original) == original

for required in ["工作中", "等待", "问题", "已完成", "status_since", "metrics", "issue_count"]:
    assert required in mod.CLIENT_IIFE, required

node = shutil.which("node")
if node:
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as fh:
        fh.write(mod.CLIENT_IIFE)
        name = fh.name
    try:
        cp = subprocess.run([node, "--check", name], text=True, capture_output=True)
        if cp.returncode:
            raise SystemExit(cp.stderr or "FAIL: CLIENT_IIFE JavaScript syntax")
    finally:
        Path(name).unlink(missing_ok=True)

print("PASS: CodePilot UI v02 upgrade and live-metrics contract")
