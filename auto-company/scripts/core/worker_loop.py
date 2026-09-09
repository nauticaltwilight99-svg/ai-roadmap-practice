"""Long-running research worker process for Docker or a VPS supervisor."""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path

from research_worker import process_one


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


if __name__ == "__main__":
    singleton = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        singleton.bind(("127.0.0.1", 48766))
        singleton.listen(1)
    except OSError:
        print("[worker] another commercial worker is already running", flush=True)
        raise SystemExit(0)
    load_env_file(Path(os.environ.get(
        "COMMERCIAL_ENV_FILE",
        r"C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\.env",
    )))
    interval = max(1, int(os.environ.get("WORKER_POLL_SECONDS", "10")))
    print(f"[worker] research loop started; interval={interval}s", flush=True)
    while True:
        processed = process_one()
        if not processed:
            time.sleep(interval)
