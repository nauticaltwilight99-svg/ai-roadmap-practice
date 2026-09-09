import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "metrics_store.py"
SPEC = importlib.util.spec_from_file_location("metrics_store", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
metrics_store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics_store)


class MetricsStoreTests(unittest.TestCase):
    def test_write_and_read_follow_n8n_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "metrics.sqlite3")
            with mock.patch.dict(os.environ, {"METRICS_DB": database}, clear=False):
                result = metrics_store.write_metric("спорт", "шаги", 8500, "шагов", "вечер")
                rows = metrics_store.get_metrics("спорт", 20)

        self.assertIn("Записано: шаги", result)
        self.assertIn("[спорт] шаги: 8500 шагов (вечер)", rows)

    def test_empty_store_has_n8n_compatible_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "metrics.sqlite3")
            with mock.patch.dict(os.environ, {"METRICS_DB": database}, clear=False):
                self.assertEqual(metrics_store.get_metrics(), "Метрики ещё не записаны.")

    def test_metrics_are_isolated_by_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "metrics.sqlite3")
            with mock.patch.dict(os.environ, {"METRICS_DB": database}, clear=False):
                metrics_store.write_metric("спорт", "шаги", 100, owner_id="user-a")
                metrics_store.write_metric("спорт", "шаги", 200, owner_id="user-b")
                user_a = metrics_store.get_metrics(owner_id="user-a")
                user_b = metrics_store.get_metrics(owner_id="user-b")

        self.assertIn("100", user_a)
        self.assertNotIn("200", user_a)
        self.assertIn("200", user_b)


if __name__ == "__main__":
    unittest.main()
