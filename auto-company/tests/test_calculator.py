import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "calculator.py"
SPEC = importlib.util.spec_from_file_location("calculator", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
calculator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(calculator)


class CalculatorTests(unittest.TestCase):
    def test_calculates_arithmetic(self) -> None:
        self.assertEqual(calculator.calculate("(12 + 8) * 3 / 2"), "30")

    def test_rejects_code_execution(self) -> None:
        result = calculator.calculate("__import__('os').system('whoami')")
        self.assertTrue(result.startswith("calculator error:"))


if __name__ == "__main__":
    unittest.main()
