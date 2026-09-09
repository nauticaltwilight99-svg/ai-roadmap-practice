import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "site_generator.py"
SPEC = importlib.util.spec_from_file_location("site_generator", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
site_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(site_generator)


class SiteGeneratorTests(unittest.TestCase):
    def test_preview_escapes_untrusted_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = site_generator.generate_preview(
                Path(directory),
                {
                    "id": "preview-1",
                    "title": "<script>bad</script>",
                    "target": "https://example.com",
                    "content": "<img src=x> offer",
                },
            )
            content = path.read_text(encoding="utf-8")

        self.assertNotIn("<script>bad</script>", content)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt;", content)

    def test_demo_preview_contains_audit_and_escapes_business_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = site_generator.generate_demo_preview(
                Path(directory),
                "<Cafe>",
                "https://example.com",
                {"summary": "Weak CTA", "weaknesses": ["нет CTA"]},
                "hospitality-web-upgrade",
                "lead-1",
            )
            content = path.read_text(encoding="utf-8")

        self.assertIn("&lt;Cafe&gt;", content)
        self.assertIn("Weak CTA", content)
        self.assertIn("нет CTA", content)
        self.assertIn("забронировать", content)


if __name__ == "__main__":
    unittest.main()
