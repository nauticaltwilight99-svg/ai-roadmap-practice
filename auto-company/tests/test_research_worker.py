import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "research_worker.py"
SPEC = importlib.util.spec_from_file_location("research_worker", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
research_worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research_worker)


class ResearchWorkerTests(unittest.TestCase):
    def test_worker_creates_approval_from_research_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "TASKS_DB": str(Path(directory) / "tasks.sqlite3"),
                "LEADS_DB": str(Path(directory) / "leads.sqlite3"),
                "APPROVALS_DB": str(Path(directory) / "approvals.sqlite3"),
                "TELEGRAM_OWNER_CHAT_ID": "42",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                from lead_store import add_lead
                from task_store import enqueue
                from approval_store import pending_for_chat

                lead = add_lead("hospitality", "Hotel Alpha", "https://example.com")
                enqueue(
                    "research_lead",
                    json.dumps(
                        {
                            "lead_id": lead["id"],
                            "website": "https://example.com",
                            "niche_id": "hospitality-web-upgrade",
                        }
                    ),
                    "research-1",
                )
                with mock.patch.object(
                    research_worker,
                    "inspect_site",
                    return_value={
                        "ok": True,
                        "title": "Hotel Alpha",
                        "summary": "Weak SEO",
                        "public_email": "hotel@example.com",
                    },
                ), mock.patch.object(
                    research_worker,
                    "generate_personalized_email",
                    return_value=("Персональное предложение", "Здравствуйте!\n\nДемо: https://demo.example/lead.html\n\nЕсли неактуально, ответьте «неактуально»."),
                ), mock.patch.object(
                    research_worker,
                    "capture_demo",
                    return_value=Path(directory) / "lead-demo.png",
                ):
                    self.assertTrue(research_worker.process_one())
                approvals = pending_for_chat(42)
                leads = __import__("lead_store").list_leads(status="drafted")

        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]["title"], "Персональное предложение")
        self.assertEqual(approvals[0]["lead_id"], lead["id"])
        self.assertEqual(approvals[0]["action_type"], "email")
        self.assertEqual(approvals[0]["target"], "hotel@example.com")
        self.assertIn("неактуально", approvals[0]["content"])
        self.assertEqual(approvals[0]["title"], "Персональное предложение")
        self.assertEqual(leads[0]["id"], lead["id"])
        self.assertEqual(leads[0]["contact"], "hotel@example.com")


if __name__ == "__main__":
    unittest.main()
