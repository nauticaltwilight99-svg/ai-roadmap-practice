import os
import unittest
from unittest import mock

from scripts.core import payment_provider


class PaymentProviderTests(unittest.TestCase):
    def test_empty_payment_url_returns_manual_instructions(self) -> None:
        with mock.patch.dict(os.environ, {"PAYMENT_URL": ""}, clear=False):
            result = payment_provider.payment_instructions()
        self.assertIn("реквизит", result.lower())
        self.assertNotIn("https://", result)

    def test_payment_url_requires_https(self) -> None:
        with mock.patch.dict(os.environ, {"PAYMENT_URL": "http://pay.example"}, clear=False):
            with self.assertRaises(ValueError):
                payment_provider.payment_url()

    def test_https_payment_url_is_added_to_proposal(self) -> None:
        with mock.patch.dict(os.environ, {"PAYMENT_URL": "https://pay.example/order/1"}, clear=False):
            result = payment_provider.payment_instructions("99 EUR")
        self.assertIn("https://pay.example/order/1", result)
        self.assertIn("Мой налог", result)


if __name__ == "__main__":
    unittest.main()
