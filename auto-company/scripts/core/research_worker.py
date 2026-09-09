"""Worker that turns queued lead research tasks into approval drafts."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

from approval_store import create_approval
from copywriter_agent import generate_personalized_email
from demo_capture import capture_demo
from lead_store import update_contact, update_status
from site_research import inspect_site
from task_store import claim, finish, is_cancelled, retry
from telegram_bot import send_message_with_actions
from quality_gate import check_html, check_text, fix_text, visual_review
from site_generator import generate_demo_preview


WORKER_ID = os.environ.get("RESEARCH_WORKER_ID", f"research-{socket.gethostname()}")
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "commercial_mvp.json"


def process_one() -> bool:
    task = claim(WORKER_ID)
    if task is None:
        return False
    try:
        payload = json.loads(str(task["payload"]))
        report = inspect_site(str(payload["website"]))
        lead_id = str(payload["lead_id"])
        if report.get("public_email"):
            update_contact(lead_id, str(report["public_email"]))
        update_status(lead_id, "researched", json.dumps(report, ensure_ascii=False))
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        niche = next(
            (item for item in config.get("starting_niches", []) if item.get("id") == payload.get("niche_id")),
            {},
        )
        preview = generate_demo_preview(
            Path(__file__).resolve().parents[2] / "outbox",
            str(report.get("title") or payload["website"]),
            str(payload["website"]),
            report,
            str(payload.get("niche_id", "")),
            lead_id,
        )
        image_path = capture_demo(preview, preview.with_suffix(".png"))
        demo_reference = f"/demo/{preview.name}"
        public_url = os.environ.get("PUBLIC_DASHBOARD_URL", "").strip().rstrip("/")
        preview_url = f"{public_url}{demo_reference}" if public_url else ""
        image_url = f"{public_url}/demo/{image_path.name}" if public_url else ""
        artifact_issues = [
            issue for issue in check_html(preview)
            if "нормализация пробелов" not in issue
        ] + [
            f"visual:{issue}" for issue in visual_review(preview).get("issues", [])
        ]
        if artifact_issues:
            raise ValueError("demo quality gate blocked artifact: " + "; ".join(artifact_issues))
        quality_issues = check_text(
            fix_text(f"Готовое персональное demo: {preview_url}\nПревью: {image_url}")
        )
        if quality_issues:
            raise ValueError("quality gate blocked draft: " + "; ".join(quality_issues))
        approval_type = "research_report"
        approval_target = str(payload["website"])
        approval_title = f"Готовое demo улучшения сайта: {report.get('title') or payload['website']}"
        approval_content = (
            "✅ Клиентский пакет подготовлен и прошёл техническую и визуальную проверку.\n\n"
            f"Открыть готовое demo: {preview_url or demo_reference}\n"
            f"Открыть превью PNG: {image_url or image_path.name}\n\n"
            "Внутренняя проверка:\n"
            f"- digital-score исходного сайта: {report.get('digital_score', 0)}/100\n"
            f"- арт-директор: {report.get('art_director', {}).get('verdict', 'Требуется ручная проверка.')}\n"
            f"- точки роста: {', '.join(str(item) for item in report.get('weaknesses', [])) or 'явных базовых проблем не найдено'}"
        )
        if report.get("public_email"):
            email_subject, email_content = generate_personalized_email(
                str(report.get("title") or payload["website"]),
                str(payload["website"]),
                str(niche.get("segment", payload.get("niche_id", ""))),
                str(report.get("summary", "Исследование завершено.")),
                [str(item) for item in report.get("weaknesses", [])],
                preview_url,
            )
            approval_type = "email"
            approval_target = str(report["public_email"])
            approval_content = fix_text(
                "✅ Готовое клиентское письмо и demo прошли проверки.\n"
                f"Demo: {preview_url or demo_reference}\n"
                f"PNG-превью: {image_url or image_path.name}\n\n"
                f"{email_content}"
            )
            email_quality_issues = check_text(approval_content)
            if email_quality_issues:
                raise ValueError("email quality gate blocked draft: " + "; ".join(email_quality_issues))
        if is_cancelled(str(task["id"])):
            return False
        create_approval(
            int(payload.get("chat_id", os.environ.get("TELEGRAM_OWNER_CHAT_ID", "0"))),
            approval_type,
            approval_target,
            email_subject if approval_type == "email" else approval_title,
            approval_content,
            lead_id=lead_id,
        )
        update_status(lead_id, "drafted", json.dumps(report, ensure_ascii=False))
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = int(payload.get("chat_id", os.environ.get("TELEGRAM_OWNER_CHAT_ID", "0")))
        if token and chat_id:
            from approval_store import pending_for_chat

            approvals = pending_for_chat(chat_id)
            if approvals:
                send_message_with_actions(token, chat_id, approvals[-1])
        finish(str(task["id"]), "completed")
        return True
    except Exception as error:
        error_text = f"{type(error).__name__}: {error}"
        if not retry(str(task["id"]), error_text):
            finish(str(task["id"]), "failed", error_text)
        return False


if __name__ == "__main__":
    print(f"processed={int(process_one())}")
