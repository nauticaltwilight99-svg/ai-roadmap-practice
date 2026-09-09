import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.core import demo_capture


class DemoCaptureTests(unittest.TestCase):
    def test_capture_requires_png_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "demo.html"
            html_path.write_text("<html></html>", encoding="utf-8")
            with self.assertRaises(ValueError):
                demo_capture.capture_demo(html_path, Path(directory) / "demo.jpg")

    def test_capture_writes_png_from_browser(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "demo.html"
            output_path = root / "demo.png"
            html_path.write_text("<html></html>", encoding="utf-8")

            def fake_run(*args: object, **kwargs: object) -> mock.Mock:
                output_path.write_bytes(b"\x89PNG\r\n")
                return mock.Mock(returncode=0, stderr="")

            with mock.patch.object(demo_capture, "_browser_path", return_value="edge.exe"), mock.patch.object(
                demo_capture.subprocess, "run", side_effect=fake_run
            ):
                result = demo_capture.capture_demo(html_path, output_path)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
