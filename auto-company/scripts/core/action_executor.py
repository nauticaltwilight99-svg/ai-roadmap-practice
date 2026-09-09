"""Execute approved actions with an explicit dry-run boundary."""

from __future__ import annotations

import os
from pathlib import Path

from brevo_client import add_contact, send_email
from lead_store import update_status
from site_generator import generate_preview

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTBOX = PROJECT_ROOT / "outbox"
LOCAL_ACTIONS = {"product_draft", "research_report", "hotel_report", "restaurant_report"}
EXTERNAL_ACTIONS = {"email", "marketplace", "crm", "telegram_message"}


def execute_approved_action(action: dict[str, str]) -> str:
    action_type = action.get("action_type", "")
    mode = os.environ.get("AUTO_ACTION_MODE", "dry_run").strip().lower()
    if mode != "live":
        mode = "dry_run"

    if action_type in LOCAL_ACTIONS:
        OUTBOX.mkdir(parents=True, exist_ok=True)
        artifact = OUTBOX / f"{action['id']}-{action_type}.md"
        artifact.write_text(
            f"# {action['title']}\n\n"
            f"- Тип: `{action_type}`\n"
            f"- Адресат: `{action['target']}`\n"
            f"- Режим: `{mode}`\n\n"
            f"{action['content']}\n",
            encoding="utf-8",
        )
        outputs = [str(artifact.relative_to(PROJECT_ROOT))]
        if action_type in {"research_report", "product_draft"}:
            preview = generate_preview(OUTBOX, action)
            outputs.append(str(preview.relative_to(PROJECT_ROOT)))
        if action.get("lead_id"):
            update_status(action["lead_id"], "drafted")
        return f"Созданы артефакты: {', '.join(outputs)}"

    if action_type in EXTERNAL_ACTIONS:
        crm_live = action_type == "crm" and os.environ.get("BREVO_AUTO_CRM", "0") == "1"
        if mode != "live" and not crm_live:
            return f"Dry-run: внешняя отправка не выполнена ({action_type} → {action['target']})."
        if action_type == "crm":
            add_contact(action["target"], action.get("title", ""))
            return f"Контакт добавлен в Brevo CRM: {action['target']}"
        if action_type == "email":
            content = action["content"]
            preview_image_url = ""
            for line in content.splitlines():
                if line.startswith("Превью изображения:"):
                    preview_image_url = line.split(":", 1)[1].strip()
                    break
            if content.startswith("Демо доступно в dashboard:"):
                content = content.split("\n\n", 1)[1] if "\n\n" in content else content
            send_email(action["target"], action["title"], content, preview_image_url=preview_image_url)
            if action.get("lead_id"):
                update_status(action["lead_id"], "contacted")
            return f"Email отправлен через Brevo: {action['target']}"
        return f"Коннектор для {action_type} ещё не настроен; отправка не выполнена."

    return f"Действие {action_type or 'unknown'} не поддерживается; отправка не выполнена."
