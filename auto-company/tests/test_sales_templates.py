import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "sales_templates.py"
SPEC = importlib.util.spec_from_file_location("sales_templates", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
sales_templates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sales_templates)


class SalesTemplateTests(unittest.TestCase):
    def test_first_demo_email_is_personalized_and_low_pressure(self) -> None:
        subject, content = sales_templates.first_demo_email(
            "Cafe Test", "https://example.com", "На первом экране неясен путь к бронированию."
        )
        self.assertIn("Cafe Test", subject)
        self.assertIn("бесплатн", content.lower())
        self.assertIn("https://example.com", content)
        self.assertIn("неактуально", content)

    def test_follow_up_contains_opt_out(self) -> None:
        _, content = sales_templates.follow_up_email("Cafe Test")
        self.assertIn("неактуально", content)


if __name__ == "__main__":
    unittest.main()
