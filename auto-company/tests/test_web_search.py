import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "web_search.py"
SPEC = importlib.util.spec_from_file_location("web_search", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
web_search = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(web_search)


class WebSearchTests(unittest.TestCase):
    def test_lite_result_parser_extracts_title_url_and_snippet(self) -> None:
        parser = web_search._DuckDuckGoParser()
        parser.feed(
            """
            <a class='result-link' href='//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs'>Docs</a>
            <td class='result-snippet'>A short result.</td>
            """
        )
        self.assertEqual(
            parser.results,
            [{"title": "Docs", "url": "https://example.com/docs", "snippet": "A short result."}],
        )

    def test_private_urls_are_rejected(self) -> None:
        self.assertEqual(web_search._clean_url("http://127.0.0.1:8787"), "")
        self.assertEqual(web_search._clean_url("file:///etc/passwd"), "")


if __name__ == "__main__":
    unittest.main()
