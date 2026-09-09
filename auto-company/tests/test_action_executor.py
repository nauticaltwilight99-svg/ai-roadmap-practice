import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "action_executor.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("action_executor", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
action_executor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(action_executor)


class ActionExecutorTests(unittest.TestCase):
    def test_product_draft_creates_outbox_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(action_executor, "PROJECT_ROOT", root), mock.patch.object(
                action_executor, "OUTBOX", root / "outbox"
            ):
                result = action_executor.execute_approved_action(
                    {
                        "id": "abc123",
                        "action_type": "product_draft",
                        "target": "marketplace",
                        "title": "Test card",
                        "content": "Description",
                    }
                )
                artifact = root / "outbox" / "abc123-product_draft.md"
                self.assertTrue(artifact.exists())
                self.assertIn("Созданы артефакты", result)
                self.assertIn("Description", artifact.read_text(encoding="utf-8"))

    def test_external_action_defaults_to_dry_run(self) -> None:
        result = action_executor.execute_approved_action(
            {
                "id": "abc123",
                "action_type": "email",
                "target": "partner@example.com",
                "title": "Offer",
                "content": "Демо доступно в dashboard: /demo/lead.html\n\nHello",
            }
        )
        self.assertIn("Dry-run", result)

    def test_approved_email_uses_brevo_and_updates_lead(self) -> None:
        with mock.patch.object(action_executor, "send_email") as send_email, mock.patch.object(
            action_executor, "update_status"
        ) as update_status, mock.patch.dict(action_executor.os.environ, {"AUTO_ACTION_MODE": "live"}):
            result = action_executor.execute_approved_action(
                {
                    "id": "abc123",
                    "action_type": "email",
                    "target": "partner@example.com",
                    "title": "Offer",
                    "content": "Hello",
                    "lead_id": "lead-1",
                }
            )
        send_email.assert_called_once_with(
            "partner@example.com", "Offer", "Hello", preview_image_url=""
        )
        update_status.assert_called_once_with("lead-1", "contacted")
        self.assertIn("отправлен", result)


if __name__ == "__main__":
    unittest.main()
