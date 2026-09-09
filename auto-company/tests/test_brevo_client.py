import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "brevo_client.py"
SPEC = importlib.util.spec_from_file_location("brevo_client", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
brevo_client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(brevo_client)


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"id": "ok"}'


class BrevoClientTests(unittest.TestCase):
    def test_add_contact_uses_brevo_api(self) -> None:
        with mock.patch.dict(os.environ, {"BREVO_API_KEY": "test-key"}, clear=False), mock.patch.object(
            brevo_client, "urlopen", return_value=FakeResponse()
        ) as request:
            result = brevo_client.add_contact("owner@example.com", "Owner")

        self.assertEqual(result["id"], "ok")
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.brevo.com/v3/contacts")
        self.assertEqual(json.loads(sent.data.decode("utf-8"))["email"], "owner@example.com")
        self.assertEqual(sent.headers["Api-key"], "test-key")

    def test_invalid_email_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            brevo_client.send_email("not-an-email", "Subject", "Body")

    def test_email_uses_coral_html_design_and_demo_link(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"BREVO_API_KEY": "test-key", "BREVO_SENDER_EMAIL": "sender@example.com"},
            clear=False,
        ), mock.patch.object(brevo_client, "urlopen", return_value=FakeResponse()) as request:
            brevo_client.send_email(
                "owner@example.com",
                "Subject",
                "Демо: https://demo.example/view",
                preview_image_url="https://demo.example/view.png",
            )
        payload = json.loads(request.call_args.args[0].data.decode("utf-8"))
        self.assertIn("#fff7f4", payload["htmlContent"])
        self.assertIn("https://demo.example/view", payload["htmlContent"])
        self.assertIn("Персональное preview демо", payload["htmlContent"])


if __name__ == "__main__":
    unittest.main()
