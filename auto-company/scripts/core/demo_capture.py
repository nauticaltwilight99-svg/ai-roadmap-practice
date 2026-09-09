"""Capture a static demo page as a reviewable PNG preview."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import quote


EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def _browser_path() -> str:
    configured = os.environ.get("DEMO_BROWSER_PATH", "").strip()
    if configured and Path(configured).is_file():
        return configured
    for candidate in EDGE_PATHS:
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("Microsoft Edge is required to capture demo previews")


def capture_demo(html_path: Path, output_path: Path) -> Path:
    if not html_path.is_file() or html_path.suffix.lower() != ".html":
        raise ValueError("a generated HTML demo is required")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".png":
        raise ValueError("preview output must be PNG")
    output_path.unlink(missing_ok=True)
    file_url = "file:///" + quote(str(html_path.resolve()).replace("\\", "/"), safe="/:")
    command = [
        _browser_path(),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "--window-size=1200,900",
        f"--screenshot={output_path}",
        file_url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=int(os.environ.get("DEMO_CAPTURE_TIMEOUT", "45")),
    )
    if completed.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"demo screenshot failed: {completed.stderr.strip()}")
    return output_path
