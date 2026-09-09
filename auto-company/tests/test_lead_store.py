import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "lead_store.py"
SPEC = importlib.util.spec_from_file_location("lead_store", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
lead_store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lead_store)


class LeadStoreTests(unittest.TestCase):
    def test_duplicate_lead_is_not_created_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"LEADS_DB": str(Path(directory) / "leads.sqlite3")}, clear=False):
                first = lead_store.add_lead("hospitality", "Hotel One", "https://hotel.test", rating=4.6)
                duplicate = lead_store.add_lead("hospitality", "Hotel One", "https://hotel.test", rating=4.6)
                leads = lead_store.list_leads()

        self.assertTrue(first["created"])
        self.assertFalse(duplicate["created"])
        self.assertEqual(len(leads), 1)

    def test_status_update_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"LEADS_DB": str(Path(directory) / "leads.sqlite3")}, clear=False):
                lead = lead_store.add_lead("local", "Business")
                self.assertTrue(lead_store.update_status(lead["id"], "researched"))
                researched = lead_store.list_leads("researched")

        self.assertEqual(researched[0]["business_name"], "Business")


if __name__ == "__main__":
    unittest.main()
