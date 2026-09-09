import importlib.util
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "core" / "site_research.py"
SPEC = importlib.util.spec_from_file_location("site_research", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
site_research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(site_research)


class SiteResearchTests(unittest.TestCase):
    def test_page_parser_extracts_quality_signals(self) -> None:
        parser = site_research._PageParser()
        parser.feed(
            '<html><head><title>Hotel Alpha</title><meta name="viewport" content="width=device-width"><meta name="description" content="Stay"></head><body><a href="/rooms">Rooms</a>'
            + (" useful text" * 130)
            + "</body></html>"
        )
        self.assertEqual(parser.title.strip(), "Hotel Alpha")
        self.assertEqual(parser.links, 1)
        self.assertIn("useful", " ".join(parser.text))

    def test_local_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            site_research._public_host("http://127.0.0.1:8787")

    def test_quality_report_includes_commercial_priority_score(self) -> None:
        response = mock.MagicMock()
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.read.return_value = (
            b"<html><head><title>Clinic</title></head><body>Dental clinic clinic@example.com</body></html>"
        )
        response.__enter__.return_value = response
        with mock.patch.object(site_research, "_public_host", return_value="https://example.com"), mock.patch.object(
            site_research, "urlopen", return_value=response
        ):
            report = site_research.inspect_site("https://example.com")
        self.assertIn("digital_score", report)
        self.assertEqual(report["priority"], "high")
        self.assertEqual(report["public_email"], "clinic@example.com")
        self.assertIn("не найден явный призыв к действию", report["weaknesses"])

    def test_aggregator_is_classified_and_exposes_external_sites(self) -> None:
        response = mock.MagicMock()
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.read.return_value = (
            b'<html><head><title>Clinics in Minsk</title></head>'
            b'<body><a href="https://clinic.example">Clinic</a></body></html>'
        )
        response.__enter__.return_value = response
        with mock.patch.object(site_research, "_public_host", return_value="https://www.103.by/cat/med/stomatologii/"), mock.patch.object(
            site_research, "urlopen", return_value=response
        ):
            report = site_research.inspect_site("https://www.103.by/cat/med/stomatologii/")
        self.assertEqual(report["page_type"], "aggregator")
        self.assertTrue(report["art_director"]["is_aggregator"])
        self.assertEqual(report["candidate_links"][0]["url"], "https://clinic.example")


if __name__ == "__main__":
    unittest.main()
