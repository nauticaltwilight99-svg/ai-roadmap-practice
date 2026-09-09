import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "commercial_worker.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("commercial_worker", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
commercial_worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(commercial_worker)


class CommercialWorkerTests(unittest.TestCase):
    def test_discovery_saves_leads_and_research_tasks(self) -> None:
        raw_results = (
            "1. Hotel Alpha\nURL: https://alpha.example\nGreat hotel\n\n"
            "2. Restaurant Beta\nURL: https://beta.example\nGreat restaurant"
        )
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(
                os.environ,
                {
                    "LEADS_DB": str(Path(directory) / "leads.sqlite3"),
                    "TASKS_DB": str(Path(directory) / "tasks.sqlite3"),
                },
                clear=False,
            ), mock.patch.object(commercial_worker, "search_web", return_value=raw_results):
                result = commercial_worker.discover_leads("hospitality-web-upgrade", "hotels", 2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["task"]["kind"], "research_lead")
        self.assertEqual(result[1]["lead"]["status"], "new")

    def test_unknown_niche_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            commercial_worker.discover_leads("missing", "query")

    def test_config_has_belarus_and_kazakhstan_priority_markets(self) -> None:
        config = commercial_worker.load_config()
        market_ids = {market["id"] for market in config["target_markets"]}
        self.assertEqual(market_ids, {"belarus", "kazakhstan"})
        priority_niches = [niche for niche in config["starting_niches"] if niche.get("priority")]
        self.assertEqual(
            {niche["segment"] for niche in priority_niches[:2]},
            {"dentistry", "horeca"},
        )


if __name__ == "__main__":
    unittest.main()
