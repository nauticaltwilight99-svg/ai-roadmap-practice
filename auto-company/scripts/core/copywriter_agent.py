"""AI copywriter for one-to-one, reviewable sales emails."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from quality_gate import check_text, fix_text


ROOT = Path(__file__).resolve().parents[2]


def generate_personalized_email(
    business_name: str,
    website: str,
    niche: str,
    audit_summary: str,
    weaknesses: list[str],
    preview_url: str,
) -> tuple[str, str]:
    prompt = f"""Ты — senior B2B copywriter FDA Solutions. Напиши одно уникальное деловое-кэжуал письмо конкретному бизнесу.
Получатель: {business_name}
Сайт: {website}
Ниша: {niche}
Аудит: {audit_summary}
Найденные точки роста: {", ".join(weaknesses[:3])}
Демо: {preview_url}

Стиль: доброжелательно, конкретно, без давления, 120–180 слов, на русском.
Письмо должно быть готово к отправке клиенту: сообщи, что для его бизнеса уже подготовлен
персональный концепт улучшенной страницы, и пригласи посмотреть результат.
Обязательно: персональная деталь из аудита, одна понятная CTA-ссылка,
цена 49–99 EUR только как ориентир после согласования, opt-out фраза.
Не называй это бесплатным демо, бесплатным аудитом или предложением «сделать улучшение потом».
Не используй клише массовой рассылки, ложные обещания, эмодзи, markdown и placeholders.
Верни только JSON без markdown: {{"subject":"...","body":"..."}}"""
    script = ROOT / "scripts" / "core" / "provider-agent.py"
    env = os.environ.copy()
    env["OLLAMA_ENABLE_TOOLS"] = "0"
    env["OLLAMA_MODEL"] = os.environ.get("COPYWRITER_MODEL", "qwen3:4b")
    env["OLLAMA_SMART_MODEL"] = ""
    env["OLLAMA_NUM_CTX"] = os.environ.get("COPYWRITER_NUM_CTX", "2048")
    env["OLLAMA_NUM_PREDICT"] = os.environ.get("COPYWRITER_NUM_PREDICT", "512")
    process = subprocess.run(
        [sys.executable, str(script)],
        input=prompt.encode("utf-8"),
        capture_output=True,
        cwd=ROOT,
        env=env,
        timeout=int(os.environ.get("COPYWRITER_TIMEOUT", "180")),
    )
    stdout_bytes = process.stdout if isinstance(process.stdout, bytes) else process.stdout.encode("utf-8")
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    if "\ufffd" in stdout:
        stdout = stdout_bytes.decode("cp1251", errors="replace")
    if process.returncode != 0 or not stdout.strip():
        raise RuntimeError("AI copywriter did not return a draft")
    raw = stdout.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("AI copywriter returned non-JSON output") from error
        result = json.loads(match.group(0))
    subject = fix_text(str(result.get("subject", "")))
    body = fix_text(str(result.get("body", "")))
    if not subject or not body:
        raise ValueError("AI copywriter returned an incomplete draft")
    issues = check_text(f"{subject}\n{body}")
    if issues:
        raise ValueError("copywriter quality gate blocked draft: " + "; ".join(issues))
    if "неактуально" not in body.lower():
        raise ValueError("copywriter draft has no opt-out")
    if preview_url and preview_url not in body:
        raise ValueError("copywriter draft has no demo link")
    return subject, body
