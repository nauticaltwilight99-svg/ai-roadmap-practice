import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "task_store.py"
SPEC = importlib.util.spec_from_file_location("task_store", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
task_store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(task_store)


class TaskStoreTests(unittest.TestCase):
    def test_enqueue_is_idempotent_and_claim_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TASKS_DB": str(Path(directory) / "tasks.sqlite3")}, clear=False):
                first = task_store.enqueue("product_draft", "{}", "campaign-1")
                duplicate = task_store.enqueue("product_draft", "{}", "campaign-1")
                claimed = task_store.claim("worker-a")
                second_claim = task_store.claim("worker-b")

        self.assertTrue(first["created"])
        self.assertFalse(duplicate["created"])
        self.assertEqual(claimed["id"], first["id"])
        self.assertIsNone(second_claim)

    def test_failed_task_can_retry_until_attempt_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TASKS_DB": str(Path(directory) / "tasks.sqlite3")}, clear=False):
                task = task_store.enqueue("research", "{}", "research-1", max_attempts=2)
                claimed = task_store.claim("worker-a")
                self.assertTrue(task_store.retry(claimed["id"], "temporary failure", 0))
                claimed_again = task_store.claim("worker-a")
                self.assertFalse(task_store.retry(claimed_again["id"], "final failure", 0))

        self.assertEqual(claimed_again["attempts"], 2)

    def test_cancel_for_chat_cancels_queued_and_running_research(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TASKS_DB": str(Path(directory) / "tasks.sqlite3")}, clear=False):
                queued = task_store.enqueue(
                    "research_lead",
                    json.dumps({"chat_id": 42}),
                    "research-queued",
                )
                running = task_store.enqueue(
                    "research_lead",
                    json.dumps({"chat_id": 42}),
                    "research-running",
                )
                task_store.claim("worker-a")
                other = task_store.enqueue(
                    "research_lead",
                    json.dumps({"chat_id": 99}),
                    "research-other",
                )
                counts = task_store.cancel_for_chat(42)
                remaining = task_store.claim("worker-b")
                queued_cancelled = task_store.is_cancelled(queued["id"])
                running_cancelled = task_store.is_cancelled(running["id"])

        self.assertEqual(counts, {"queued": 1, "running": 1})
        self.assertEqual(remaining["id"], other["id"])
        self.assertTrue(queued_cancelled)
        self.assertTrue(running_cancelled)


if __name__ == "__main__":
    unittest.main()
