import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "agent_orchestrator.py"
import sys
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("agent_orchestrator", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
agent_orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent_orchestrator)


class AgentOrchestratorTests(unittest.TestCase):
    def test_team_has_six_roles_and_quality_is_final_gate(self) -> None:
        team = agent_orchestrator.load_team()
        self.assertEqual(len(team["team"]), 6)
        self.assertEqual(team["execution"]["telegram_gate"], "quality_guardian")
        self.assertEqual(team["execution"]["order"][-1], "quality_guardian")

    def test_run_starts_with_research_and_advances_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TASKS_DB": str(Path(directory) / "tasks.sqlite3")}, clear=False):
                run = agent_orchestrator.create_run("Подготовить сайт", 42)
                next_stage = agent_orchestrator.advance_run(
                    run["run_id"], 42, "Подготовить сайт", "research", {"sources": []}
                )

        self.assertEqual(run["first_role"], "research")
        self.assertEqual(next_stage["next_role"], "strategy")

    def test_telegram_is_blocked_without_quality_pass(self) -> None:
        with self.assertRaises(ValueError):
            agent_orchestrator.advance_run(
                "run", 42, "request", "quality_guardian", {"quality_pass": False, "quality_round": 2}
            )

    def test_failed_quality_returns_to_content_design(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TASKS_DB": str(Path(directory) / "tasks.sqlite3")}, clear=False):
                result = agent_orchestrator.advance_run(
                    "run-revise", 42, "request", "quality_guardian", {"quality_pass": False, "quality_round": 0}
                )
        self.assertTrue(result["revision"])
        self.assertEqual(result["next_role"], "content_design")


if __name__ == "__main__":
    unittest.main()
