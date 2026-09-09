import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "telegram_bot.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("telegram_bot", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
telegram_bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telegram_bot)


class TelegramBotTests(unittest.TestCase):
    def test_memory_round_trip_is_scoped_to_chat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"TELEGRAM_MEMORY_DB": str(Path(directory) / "memory.sqlite3")}, clear=False):
                telegram_bot.remember(10, "user", "Привет")
                telegram_bot.remember(11, "user", "Чужой чат")
                history = telegram_bot.recent_memory(10)

        self.assertIn("user: Привет", history)
        self.assertNotIn("Чужой чат", history)

    def test_allowed_chat_ids_can_restrict_access(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_CHAT_IDS": "10, 20"}, clear=False):
            self.assertTrue(telegram_bot.allowed_chat(10))
            self.assertFalse(telegram_bot.allowed_chat(30))

    def test_preview_buttons_include_public_demo_link(self) -> None:
        approval = {
            "id": "demo-1",
            "action_type": "research_report",
            "target": "https://example.com",
            "title": "Demo",
            "content": "Демо доступно в dashboard: /demo/demo-1.html",
        }
        with mock.patch.dict(os.environ, {"PUBLIC_DASHBOARD_URL": "https://demo.example"}, clear=False), mock.patch.object(
            telegram_bot, "telegram_request"
        ) as request:
            telegram_bot.send_message_with_actions("token", 1, approval)
        markup = request.call_args.args[2]["reply_markup"]["inline_keyboard"]
        self.assertEqual(markup[0][0]["url"], "https://demo.example/demo/demo-1.html")
        self.assertEqual(markup[-1][0]["callback_data"], "approve:demo-1")


if __name__ == "__main__":
    unittest.main()
