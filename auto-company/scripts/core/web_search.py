"""Small, keyless web search adapter for the Gemini execution agent."""

from __future__ import annotations

import html
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


SEARCH_URL = "https://lite.duckduckgo.com/lite/?q={}"
MAX_RESULTS = 5
MAX_QUERY_LENGTH = 300


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and {"result__a", "result-link"} & classes and len(self.results) < MAX_RESULTS:
            href = html.unescape(attributes.get("href") or "")
            redirect_url = parse_qs(urlparse(href).query).get("uddg", [""])[0]
            href = unquote(redirect_url) or href
            self._current = {"title": "", "url": href, "snippet": ""}
            self._in_title = True
        elif {"result__snippet", "result-snippet"} & classes and self.results:
            self._current = self.results[-1]
            self._in_snippet = True

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        if self._in_title:
            self._current["title"] += data
        elif self._in_snippet:
            self._current["snippet"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title and self._current is not None:
            self._current["title"] = " ".join(self._current["title"].split())
            self.results.append(self._current)
            self._current = None
            self._in_title = False
        elif tag in {"a", "div", "td"} and self._in_snippet:
            if self._current is not None:
                self._current["snippet"] = " ".join(self._current["snippet"].split())
            self._in_snippet = False


def _assert_public_host(hostname: str) -> None:
    if not hostname or hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("private or local hosts are not allowed")
    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except OSError as error:
        raise ValueError(f"could not resolve search host: {hostname}") from error
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("private or local hosts are not allowed")


def _clean_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        return ""
    try:
        _assert_public_host(parsed.hostname or "")
    except ValueError:
        return ""
    return raw_url


def search_web(query: str, max_results: int = MAX_RESULTS) -> str:
    cleaned_query = " ".join((query or "").split())[:MAX_QUERY_LENGTH]
    if not cleaned_query:
        return "search query is empty"
    limit = max(1, min(int(max_results), MAX_RESULTS))
    request = Request(
        SEARCH_URL.format(quote_plus(cleaned_query)),
        headers={"User-Agent": "AutoCompany/1.0 (+local research agent)"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            page = response.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as error:
        return f"web search error: {type(error).__name__}: {error}"

    parser = _DuckDuckGoParser()
    parser.feed(page)
    lines: list[str] = []
    for index, result in enumerate(parser.results[:limit], start=1):
        url = _clean_url(result["url"])
        if not url or not result["title"]:
            continue
        snippet = " ".join(result["snippet"].split())
        lines.append(f"{index}. {result['title']}\nURL: {url}\n{snippet}")
    return "\n\n".join(lines) if lines else "No public search results found"
