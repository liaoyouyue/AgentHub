#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
m = re.search(r"<script>([\s\S]*?)</script>", html)
if not m:
    raise SystemExit("FAIL: script block missing")
node = shutil.which("node")
if not node:
    print("SKIP: node not found")
    raise SystemExit(0)
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
    f.write(m.group(1))
    name = f.name
p = subprocess.run([node, "--check", name], text=True, capture_output=True)
Path(name).unlink(missing_ok=True)
if p.returncode:
    print(p.stderr)
    raise SystemExit("FAIL: UI JavaScript syntax")
print("PASS: UI JavaScript syntax")