import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.core import telegram_bot


class TelegramCommercialTests(unittest.TestCase):
    def test_parses_find_leads_command(self) -> None:
        self.assertEqual(
            telegram_bot._commercial_request("/find_leads Minsk dental"),
            ("Minsk", "dentistry", []),
        )

    def test_routes_research_tasks_to_requesting_chat(self) -> None:
        raw_results = "1. Demo Clinic\nURL: https://clinic.example\nClinic"
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(
                os.environ,
                {
                    "LEADS_DB": str(Path(directory) / "leads.sqlite3"),
                    "TASKS_DB": str(Path(directory) / "tasks.sqlite3"),
                },
                clear=False,
            ), mock.patch("commercial_worker.search_web", return_value=raw_results):
                result = telegram_bot._discover_requested_leads(777, "Minsk", "dentistry", [])

            self.assertIn("поставлено в исследование: 1", result)

            import sqlite3

            connection = sqlite3.connect(Path(directory) / "tasks.sqlite3")
            payload = connection.execute("SELECT payload FROM tasks").fetchone()[0]
            connection.close()
            self.assertIn('"chat_id": 777', payload)

    def test_stop_command_cancels_tasks_for_chat(self) -> None:
        with mock.patch.object(telegram_bot, "send_message") as send_message, mock.patch(
            "task_store.cancel_for_chat",
            return_value={"queued": 2, "running": 1},
        ):
            telegram_bot.handle_update(
                "token",
                {"message": {"chat": {"id": 777}, "text": "/stop_find_leads"}},
            )

        send_message.assert_called_once()
        self.assertIn("Отменено задач: 3", send_message.call_args.args[2])

    def test_status_command_is_available(self) -> None:
        with mock.patch.object(telegram_bot, "send_message") as send_message, mock.patch(
            "task_store.summary_for_chat",
            return_value={"queued": 1, "completed": 2},
        ):
            telegram_bot.handle_update(
                "token",
                {"message": {"chat": {"id": 777}, "text": "/status"}},
            )

        self.assertIn("в очереди: 1", send_message.call_args.args[2])
        self.assertIn("завершено: 2", send_message.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
