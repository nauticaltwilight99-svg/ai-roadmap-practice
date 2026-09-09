import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "approval_store.py"
SPEC = importlib.util.spec_from_file_location("approval_store", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
approval_store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(approval_store)


class ApprovalStoreTests(unittest.TestCase):
    def test_pending_action_can_be_approved_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"APPROVALS_DB": str(Path(directory) / "approvals.sqlite3")}, clear=False):
                approval_id = approval_store.create_approval(
                    42, "email", "partner@example.com", "Draft", "Hello", lead_id="lead-1"
                )
                pending = approval_store.pending_for_chat(42)
                decision = approval_store.decide(approval_id, "approved")
                after = approval_store.pending_for_chat(42)

        self.assertEqual(pending[0]["id"], approval_id)
        self.assertEqual(pending[0]["lead_id"], "lead-1")
        self.assertEqual(decision["status"], "approved")
        self.assertEqual(after, [])


if __name__ == "__main__":
    unittest.main()
