import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.core import public_demo_server


class PublicDemoServerTests(unittest.TestCase):
    def test_demo_handler_rejects_non_demo_paths(self) -> None:
        handler = object.__new__(public_demo_server.DemoHandler)
        handler.send_error = mock.Mock()
        handler.path = "/api/status"
        handler.do_GET()
        handler.send_error.assert_called_once_with(404, "Demo not found")

    def test_demo_handler_rejects_path_traversal(self) -> None:
        handler = object.__new__(public_demo_server.DemoHandler)
        handler.send_error = mock.Mock()
        handler.path = "/demo/../secret.html"
        handler.do_GET()
        handler.send_error.assert_called_once_with(400, "Invalid demo path")

    def test_demo_handler_serves_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            demo_dir = Path(directory)
            demo = demo_dir / "lead-demo.html"
            demo.write_text("<h1>demo</h1>", encoding="utf-8")
            handler = object.__new__(public_demo_server.DemoHandler)
            handler.path = "/demo/lead-demo.html"
            handler.send_response = mock.Mock()
            handler.send_header = mock.Mock()
            handler.end_headers = mock.Mock()
            handler.wfile = mock.Mock()
            with mock.patch.object(public_demo_server, "OUTBOX_DIR", demo_dir):
                handler.do_GET()
            handler.send_response.assert_called_once_with(200)
            handler.wfile.write.assert_called_once_with(b"<h1>demo</h1>")


if __name__ == "__main__":
    unittest.main()
