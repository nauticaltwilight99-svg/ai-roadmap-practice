#!/usr/bin/env python3
"""Select the configured AI provider for Telegram and workers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
provider = os.environ.get("AI_PROVIDER", "ollama").strip().lower()
script = ROOT / ("ollama-agent.py" if provider == "ollama" else "gemini-agent.py")
completed = subprocess.run(
    [sys.executable, str(script)],
    stdin=sys.stdin,
    capture_output=True,
    text=True,
    cwd=ROOT.parents[1],
    env=os.environ.copy(),
)
sys.stdout.write(completed.stdout)
sys.stderr.write(completed.stderr)
raise SystemExit(completed.returncode)
