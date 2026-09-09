"""Deterministic pre-Telegram quality gate for generated artifacts."""

from __future__ import annotations

import html
import re
from pathlib import Path


DANGEROUS_HTML = re.compile(r"<script\b|javascript:|on(?:click|load|error)\s*=", re.IGNORECASE)
PLACEHOLDERS = re.compile(r"\b(?:TODO|TBD|lorem ipsum|replace[- ]?me)\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s)]+")


def fix_text(text: str) -> str:
    """Apply only deterministic, low-risk corrections."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(lines).strip()


def check_text(text: str) -> list[str]:
    issues: list[str] = []
    if not text.strip():
        issues.append("пустой результат")
    if PLACEHOLDERS.search(text):
        issues.append("найдены незаполненные placeholders")
    if text != fix_text(text):
        issues.append("нормализация пробелов ещё не применена")
    return issues


def check_html(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return [f"не удалось прочитать HTML: {error}"]
    issues = check_text(text)
    if "<!doctype html>" not in text.lower():
        issues.append("отсутствует doctype")
    if not re.search(r"<meta[^>]+viewport", text, re.IGNORECASE):
        issues.append("отсутствует viewport")
    if DANGEROUS_HTML.search(text):
        issues.append("обнаружен потенциально опасный HTML")
    if "<title>" not in text.lower():
        issues.append("отсутствует title")
    return issues


def visual_review(path: Path) -> dict[str, object]:
    """Score presentation signals before a human approval message is sent."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return {"score": 0, "passed": False, "issues": [str(error)]}
    checks = {
        "semantic_title": bool(re.search(r"<title>[^<]{3,}</title>", text, re.IGNORECASE)),
        "responsive": bool(re.search(r"viewport", text, re.IGNORECASE)),
        "clear_heading": bool(re.search(r"<h1>[^<]{8,}</h1>", text, re.IGNORECASE)),
        "action": bool(re.search(r"<(?:a|button)\b[^>]*>[^<]{3,}</(?:a|button)>", text, re.IGNORECASE)),
        "not_placeholder": not bool(PLACEHOLDERS.search(text)),
        "not_dangerous": not bool(DANGEROUS_HTML.search(text)),
        "reasonable_length": 600 <= len(text) <= 200_000,
    }
    score = round(sum(checks.values()) / len(checks) * 100)
    issues = [name for name, passed in checks.items() if not passed]
    return {"score": score, "passed": score >= 85 and not issues, "issues": issues}


def run_quality_gate(artifact_dir: Path, content: str = "") -> dict[str, object]:
    issues = check_text(content)
    visual_reviews = []
    for path in artifact_dir.glob("*.html"):
        issues.extend(f"{path.name}: {issue}" for issue in check_html(path))
        review = visual_review(path)
        visual_reviews.append({"file": path.name, **review})
        issues.extend(f"{path.name}: visual:{issue}" for issue in review["issues"])
    return {
        "quality_pass": not issues,
        "issues": issues,
        "visual_reviews": visual_reviews,
        "checked_dir": str(artifact_dir),
    }
