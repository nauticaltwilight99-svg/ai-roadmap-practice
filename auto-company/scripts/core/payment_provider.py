"""Manual-first payment instructions for the first commercial sale."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def payment_url() -> str:
    value = os.environ.get("PAYMENT_URL", "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("PAYMENT_URL must be an HTTPS URL")
    return value


def payment_instructions(amount: str = "49–99 EUR") -> str:
    url = payment_url()
    if url:
        return (
            f"Оплата: {amount} после согласования объёма.\n"
            f"Платёжная ссылка: {url}\n"
            "После оплаты будет сформирован чек в «Мой налог»."
        )
    phone = os.environ.get("PAYMENT_PHONE", "").strip()
    recipient = os.environ.get("PAYMENT_RECIPIENT", "получателю").strip()
    purpose = os.environ.get("PAYMENT_PURPOSE", "FDA Solutions — сайт и демо").strip()
    if phone:
        return (
            f"Оплата: {amount} после согласования объёма.\n"
            f"Перевод по номеру телефона: {phone} ({recipient}).\n"
            f"Назначение: {purpose}.\n"
            "После перевода пришлите подтверждение; чек будет сформирован в «Мой налог»."
        )
    return (
        f"Оплата: {amount} после согласования объёма. "
        "Реквизиты и назначение перевода будут отправлены отдельно. "
        "После оплаты чек будет сформирован в «Мой налог»."
    )
