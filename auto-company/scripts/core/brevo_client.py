"""Minimal Brevo CRM and transactional email client."""

from __future__ import annotations

import html
import json
import os
import re
from urllib.request import Request, urlopen


API_ROOT = "https://api.brevo.com/v3"


def _request(path: str, payload: dict[str, object]) -> dict[str, object]:
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is required for live Brevo actions")
    request = Request(
        f"{API_ROOT}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"accept": "application/json", "api-key": api_key, "content-type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=int(os.environ.get("BREVO_TIMEOUT", "30"))) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def add_contact(
    email: str,
    name: str = "",
    attributes: dict[str, object] | None = None,
) -> dict[str, object]:
    email = email.strip()
    if "@" not in email:
        raise ValueError("a valid contact email is required")
    contact_attributes = dict(attributes or {})
    if name.strip():
        contact_attributes["NAME"] = name.strip()
    payload: dict[str, object] = {
        "email": email,
        "attributes": contact_attributes,
        "updateEnabled": True,
    }
    list_id = os.environ.get("BREVO_CONTACT_LIST_ID", "").strip()
    if list_id:
        try:
            payload["listIds"] = [int(list_id)]
        except ValueError as error:
            raise ValueError("BREVO_CONTACT_LIST_ID must be an integer") from error
    return _request(
        "/contacts",
        payload,
    )


def _email_html(content: str, preview_image_url: str = "") -> str:
    escaped = html.escape(content).replace("\n", "<br>")
    links = re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1" style="color:#b85f55;font-weight:700;">Открыть демо</a>',
        escaped,
    )
    image = (
        f'<img src="{html.escape(preview_image_url, quote=True)}" alt="Персональное preview демо" '
        'style="display:block;width:100%;max-width:528px;border-radius:12px;margin:24px 0 8px;">'
        if preview_image_url.startswith("https://")
        else ""
    )
    return f"""<!doctype html><html><body style="margin:0;background:#fff7f4;color:#26332f;font-family:Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fff7f4;padding:32px 12px;">
<tr><td align="center"><table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:18px;overflow:hidden;">
<tr><td style="height:8px;background:#e9a39b;"></td></tr><tr><td style="padding:32px 36px;">
<div style="color:#b85f55;font-size:12px;font-weight:bold;letter-spacing:1.5px;">FDA SOLUTIONS</div>
<div style="font-size:17px;line-height:1.7;margin-top:22px;">{links}</div>{image}
<div style="margin-top:28px;padding:18px 20px;background:#fff0ed;border-radius:12px;font-size:14px;line-height:1.5;color:#6c514d;">Персональное демо подготовлено для вашего бизнеса.</div>
</td></tr></table></td></tr></table></body></html>"""


def send_email(target: str, subject: str, content: str, preview_image_url: str = "") -> dict[str, object]:
    email = target.strip()
    if "@" not in email:
        raise ValueError("a valid recipient email is required")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    sender_name = os.environ.get(
        "BREVO_SENDER_NAME",
        "FDA Solutions: First Design Aid for HoReCa & more",
    ).strip()
    if not sender_email:
        raise RuntimeError("BREVO_SENDER_EMAIL is required for live email actions")
    return _request(
        "/smtp/email",
        {
            "sender": {"email": sender_email, "name": sender_name},
            "to": [{"email": email}],
            "subject": subject.strip() or "Предложение по улучшению сайта",
            "textContent": content.strip(),
            "htmlContent": _email_html(content, preview_image_url),
        },
    )
