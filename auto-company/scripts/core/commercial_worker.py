"""Lead discovery worker for the commercial MVP."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from lead_store import add_lead
from task_store import enqueue
from site_research import inspect_site
from web_search import search_web


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "commercial_mvp.json"


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _extract_url(block: str) -> str:
    match = re.search(r"^URL:\s*(\S+)", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_title(block: str) -> str:
    first_line = block.strip().splitlines()[0] if block.strip() else ""
    return re.sub(r"^\d+\.\s*", "", first_line).strip()


def _aggregator_candidates(website: str) -> tuple[bool, list[tuple[str, str]]]:
    try:
        report = inspect_site(website)
    except Exception:
        return False, []
    if report.get("page_type") != "aggregator":
        return False, []
    links = report.get("candidate_links", [])
    if not isinstance(links, list):
        return True, []
    return True, [
        (str(item.get("url", "")).strip(), str(item.get("label", "")).strip())
        for item in links
        if isinstance(item, dict) and str(item.get("url", "")).strip()
    ]


def discover_leads(
    niche_id: str,
    query: str,
    max_results: int = 5,
    chat_id: int | None = None,
) -> list[dict[str, object]]:
    config = load_config()
    niches = {item["id"]: item for item in config["starting_niches"]}
    niche = niches.get(niche_id)
    if niche is None:
        raise ValueError(f"unknown niche: {niche_id}")

    raw_results = search_web(query, max_results)
    if raw_results.startswith("web search error") or raw_results == "No public search results found":
        return []

    discovered: list[dict[str, object]] = []
    for block in raw_results.split("\n\n"):
        website = _extract_url(block)
        business_name = _extract_title(block)
        if not website or not business_name:
            continue
        is_aggregator, candidates = _aggregator_candidates(website)
        if candidates:
            for candidate_url, candidate_label in candidates:
                candidate_name = candidate_label or business_name
                candidate_lead = add_lead(
                    str(niche_id),
                    candidate_name,
                    website=candidate_url,
                    notes=f"Источник: агрегатор {website}; конечный сайт найден автоматически и требует арт-директорской проверки.",
                )
                task = enqueue(
                    "research_lead",
                    json.dumps(
                        {
                            "lead_id": candidate_lead["id"],
                            "niche_id": niche_id,
                            "website": candidate_url,
                            "chat_id": chat_id if chat_id is not None else int(os.environ.get("TELEGRAM_OWNER_CHAT_ID", "0")),
                        },
                        ensure_ascii=False,
                    ),
                    idempotency_key=f"research:{candidate_lead['id']}",
                )
                discovered.append({"lead": candidate_lead, "task": task, "source": website})
            continue
        if is_aggregator:
            continue
        lead = add_lead(
            str(niche_id),
            business_name,
            website=website,
            notes="Источник: публичный web search; требуется ручная проверка контактов и качества сайта.",
        )
        task = enqueue(
            "research_lead",
            json.dumps(
                {
                    "lead_id": lead["id"],
                    "niche_id": niche_id,
                    "website": website,
                    "chat_id": chat_id if chat_id is not None else int(os.environ.get("TELEGRAM_OWNER_CHAT_ID", "0")),
                },
                ensure_ascii=False,
            ),
            idempotency_key=f"research:{lead['id']}",
        )
        discovered.append({"lead": lead, "task": task})
    return discovered


def run_once() -> int:
    config = load_config()
    total = 0
    markets = config.get("target_markets", [])
    for niche in config["starting_niches"]:
        templates = niche.get("search_query_templates")
        if not isinstance(templates, list) or not templates:
            templates = [niche.get("search_query") or f"{niche['name']} website"]
        for market in markets:
            market_total = 0
            cities = market.get("cities", []) if isinstance(market, dict) else []
            for city in cities:
                for template in templates:
                    query = str(template).format(city=city)
                    found = discover_leads(str(niche["id"]), query, max_results=5)
                    market_total += len(found)
            total += market_total
            market_id = market.get("id", "market") if isinstance(market, dict) else "market"
            print(f"[{niche['id']}:{market_id}] discovered={market_total}", flush=True)
    return total


if __name__ == "__main__":
    print(f"discovered_total={run_once()}")
