import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.core import lead_store, payment_provider


class LeadPaymentTests(unittest.TestCase):
    def test_phone_transfer_instructions_are_explicit(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"PAYMENT_URL": "", "PAYMENT_PHONE": "+7 900 000-00-00", "PAYMENT_RECIPIENT": "Иван"},
            clear=False,
        ):
            result = payment_provider.payment_instructions()
        self.assertIn("+7 900 000-00-00", result)
        self.assertIn("назначение", result.lower())
        self.assertIn("Мой налог", result)

    def test_payment_is_recorded_in_lead_crm(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {"LEADS_DB": str(Path(directory) / "leads.sqlite3")}, clear=False
        ):
            lead = lead_store.add_lead("dentistry", "Clinic")
            self.assertTrue(lead_store.record_payment(lead["id"], "payment_pending", "client said paid"))
            pending = lead_store.list_leads(status="payment_pending")
            self.assertEqual(pending[0]["payment_method"], "phone_transfer")
            self.assertTrue(lead_store.record_payment(lead["id"], "paid", "receipt-001"))
            paid = lead_store.list_leads(status="paid")
            self.assertEqual(paid[0]["payment_reference"], "receipt-001")


if __name__ == "__main__":
    unittest.main()
