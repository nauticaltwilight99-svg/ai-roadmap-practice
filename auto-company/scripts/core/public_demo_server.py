"""Serve only generated demo pages for temporary public previews."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTBOX_DIR = REPO_ROOT / "outbox"
LANDING_PATH = OUTBOX_DIR / "fda-solutions.html"


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "FDA-Demo/1.0"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            if not LANDING_PATH.is_file():
                self.send_error(404, "Landing page not found")
                return
            body = LANDING_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        prefix = "/demo/"
        if not path.startswith(prefix):
            self.send_error(404, "Demo not found")
            return
        relative = Path(path.removeprefix(prefix))
        if relative.name != str(relative) or relative.suffix.lower() not in {".html", ".png"}:
            self.send_error(400, "Invalid demo path")
            return
        demo_path = OUTBOX_DIR / relative.name
        if not demo_path.is_file():
            self.send_error(404, "Demo not found")
            return
        body = demo_path.read_bytes()
        self.send_response(200)
        content_type = "image/png" if demo_path.suffix.lower() == ".png" else "text/html; charset=utf-8"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"public demo server listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
