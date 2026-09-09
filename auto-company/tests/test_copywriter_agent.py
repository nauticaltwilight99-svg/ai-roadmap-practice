import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "copywriter_agent.py"
SPEC = importlib.util.spec_from_file_location("copywriter_agent", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
copywriter_agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(copywriter_agent)


class CopywriterAgentTests(unittest.TestCase):
    def test_ai_copywriter_returns_personalized_quality_checked_draft(self) -> None:
        process = mock.Mock(returncode=0)
        process.stdout = json.dumps(
            {
                "subject": "Идея для записи в Clinic",
                "body": "Здравствуйте!\n\nНа первом экране Clinic не сразу виден путь к записи.\n"
                "Демо: https://demo.example/clinic.html\n\n"
                "Если неактуально, ответьте «неактуально».",
            },
            ensure_ascii=False,
        )
        with mock.patch.object(copywriter_agent.subprocess, "run", return_value=process):
            subject, body = copywriter_agent.generate_personalized_email(
                "Clinic",
                "https://clinic.example",
                "dentistry",
                "Путь к записи неочевиден.",
                ["нет явного CTA"],
                "https://demo.example/clinic.html",
            )
        self.assertIn("Clinic", subject)
        self.assertIn("https://demo.example/clinic.html", body)
        self.assertIn("неактуально", body)


if __name__ == "__main__":
    unittest.main()
