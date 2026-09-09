import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "ollama-agent.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("ollama_agent", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
ollama_agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ollama_agent)


class OllamaAgentTests(unittest.TestCase):
    def test_simple_prompt_uses_fast_model(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"OLLAMA_MODEL": "qwen3:4b", "OLLAMA_SMART_MODEL": "qwen3:8b"},
            clear=False,
        ):
            self.assertEqual(ollama_agent.select_model("Сколько будет 2 + 2?"), "qwen3:4b")

    def test_complex_prompt_uses_smart_model(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"OLLAMA_MODEL": "qwen3:4b", "OLLAMA_SMART_MODEL": "qwen3:8b"},
            clear=False,
        ):
            self.assertEqual(
                ollama_agent.select_model("Проанализируй и разработай стратегию продаж"),
                "qwen3:8b",
            )

    def test_telegram_context_becomes_chat_roles(self) -> None:
        messages = ollama_agent.build_messages(
            "Контекст диалога:\nuser: Привет\nassistant: Здравствуйте\n\n"
            "Новый запрос пользователя:\nЧто дальше?"
        )
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[-1]["content"], "Что дальше?")


if __name__ == "__main__":
    unittest.main()
