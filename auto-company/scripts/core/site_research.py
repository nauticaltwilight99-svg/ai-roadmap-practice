"""Bounded public-site inspection for commercial lead research."""

from __future__ import annotations

import html
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


MAX_BYTES = 1_500_000


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.text: list[str] = []
        self.links = 0
        self.link_targets: list[tuple[str, str]] = []
        self._in_title = False
        self._blocked = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._blocked = True
        if tag == "a" and attributes.get("href"):
            self.links += 1
            self.link_targets.append((attributes["href"] or "", " ".join(self.text[-3:]).strip()))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"}:
            self._blocked = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if not self._blocked:
            self.text.append(data)


def _public_host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("only public http(s) URLs are allowed")
    hostname = parsed.hostname or ""
    if not hostname or hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("local hosts are not allowed")
    addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)}
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("private hosts are not allowed")
    return url


def inspect_site(url: str) -> dict[str, object]:
    safe_url = _public_host(url)
    request = Request(safe_url, headers={"User-Agent": "AutoCompanyResearch/1.0"})
    with urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return {"url": safe_url, "ok": False, "error": "not an HTML page"}
        body = response.read(MAX_BYTES).decode("utf-8", errors="replace")

    parser = _PageParser()
    parser.feed(body)
    text = " ".join(html.unescape(" ".join(parser.text)).split())
    title = " ".join(parser.title.split())
    email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", body)
    public_email = email_match.group(0) if email_match else ""
    parsed_url = urlparse(safe_url)
    hostname = (parsed_url.hostname or "").lower()
    aggregator_hosts = ("103.by", "relax.by", "zoon.", "ydoc.", "blizko.", "talon.by", "prodoctorov.", "docdoc.", "2doc.by")
    is_aggregator = any(hostname == host or hostname.endswith("." + host) for host in aggregator_hosts)
    is_aggregator = is_aggregator or any(
        marker in parsed_url.path.lower() for marker in ("/cat/", "/list/", "/top/", "/categories/", "/service/")
    )
    signals = {
        "has_title": bool(title),
        "word_count": len(text.split()),
        "link_count": parser.links,
        "has_viewport": bool(re.search(r"name=[\"']viewport[\"']", body, re.IGNORECASE)),
        "has_description": bool(re.search(r"name=[\"']description[\"']", body, re.IGNORECASE)),
        "has_https": safe_url.lower().startswith("https://"),
        "has_cta": bool(re.search(r"(запис|звон|брон|заказ|contact|book|reserve|order|call)", text, re.IGNORECASE)),
        "has_public_email": bool(public_email),
    }
    weaknesses = []
    if not signals["has_title"]:
        weaknesses.append("нет понятного title")
    if int(signals["word_count"]) < 120:
        weaknesses.append("мало содержательного текста")
    if not signals["has_viewport"]:
        weaknesses.append("не найден mobile viewport")
    if not signals["has_description"]:
        weaknesses.append("нет SEO description")
    if not signals["has_cta"]:
        weaknesses.append("не найден явный призыв к действию")
    digital_score = 100
    digital_score -= 15 * sum(
        1 for key in ("has_title", "has_viewport", "has_description", "has_cta") if not signals[key]
    )
    digital_score -= 10 if int(signals["word_count"]) < 120 else 0
    digital_score -= 10 if not signals["has_https"] else 0
    return {
        "url": safe_url,
        "ok": True,
        "title": title,
        "signals": signals,
        "weaknesses": weaknesses,
        "digital_score": max(0, digital_score),
        "priority": "high" if digital_score < 70 else "review",
        "public_email": public_email,
        "page_type": "aggregator" if is_aggregator else "company",
        "art_director": {
            "is_aggregator": is_aggregator,
            "eligible_for_redesign": not is_aggregator and digital_score <= 90,
            "opportunity_score": max(0, 100 - digital_score),
            "verdict": "Источник discovery, не конечный клиент." if is_aggregator else (
                "Подходит для персонального redesign." if digital_score <= 90
                else "Сайт выглядит сильным; брать только при дополнительном бизнес-сигнале."
            ),
        },
        "candidate_links": [
            {"url": urljoin(safe_url, href), "label": label[:120]}
            for href, label in parser.link_targets
            if urlparse(urljoin(safe_url, href)).scheme in {"http", "https"}
            and urlparse(urljoin(safe_url, href)).netloc.lower() != hostname
        ][:20],
        "summary": f"Страница: {title or 'без заголовка'}; слабые места: {', '.join(weaknesses) or 'явных базовых проблем не найдено'}."
    }
