import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "quality_gate.py"
SPEC = importlib.util.spec_from_file_location("quality_gate", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
quality_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality_gate)


class QualityGateTests(unittest.TestCase):
    def test_fixer_normalizes_generated_text(self) -> None:
        fixed = quality_gate.fix_text("  Hello   world  \n\n Next step ")
        self.assertEqual(fixed, "Hello world\n\nNext step")
        self.assertEqual(quality_gate.check_text(fixed), [])

    def test_html_dangerous_content_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preview.html"
            path.write_text(
                '<!doctype html><html><head><title>Test</title><meta name="viewport"></head><body><script>x</script></body></html>',
                encoding="utf-8",
            )
            report = quality_gate.run_quality_gate(path.parent)

        self.assertFalse(report["quality_pass"])
        self.assertTrue(any("опасный" in issue for issue in report["issues"]))

    def test_visual_review_passes_a_complete_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preview.html"
            path.write_text(
                "<!doctype html><html><head><title>Hotel Alpha homepage</title><meta name='viewport'></head>"
                "<body><main><h1>Welcome to Hotel Alpha</h1><p>Stay near the sea.</p><a href='#book'>Book your stay</a>"
                + ("<p>Comfortable rooms, local recommendations, seasonal experiences and direct booking support.</p>" * 8)
                + "</main></body></html>",
                encoding="utf-8",
            )
            review = quality_gate.visual_review(path)

        self.assertTrue(review["passed"])
        self.assertGreaterEqual(review["score"], 85)


if __name__ == "__main__":
    unittest.main()
