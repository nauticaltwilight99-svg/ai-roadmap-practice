import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "worker_loop.py"
SPEC = importlib.util.spec_from_file_location("worker_loop", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
worker_loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker_loop)


class WorkerLoopTests(unittest.TestCase):
    def test_load_env_file_does_not_override_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("WORKER_TEST=from-file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                worker_loop.load_env_file(env_path)
                self.assertEqual(os.environ["WORKER_TEST"], "from-file")

    def test_load_env_file_preserves_process_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("WORKER_TEST=from-file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"WORKER_TEST": "from-process"}, clear=True):
                worker_loop.load_env_file(env_path)
                self.assertEqual(os.environ["WORKER_TEST"], "from-process")


if __name__ == "__main__":
    unittest.main()
