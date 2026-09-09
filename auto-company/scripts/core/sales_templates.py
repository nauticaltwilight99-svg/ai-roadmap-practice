"""Small, human-reviewable sales email templates for FDA Solutions."""

from __future__ import annotations

from payment_provider import payment_instructions

BRAND = "FDA Solutions: First Design Aid for HoReCa & more"


def first_demo_email(
    business_name: str,
    website: str,
    audit_summary: str,
    preview_url: str = "",
) -> tuple[str, str]:
    subject = f"{business_name}: бесплатное демо улучшения сайта"
    preview_line = f"\nДемо: {preview_url}\n" if preview_url else ""
    content = (
        f"Здравствуйте!\n\n"
        f"Я подготовил короткий бесплатный разбор сайта {business_name} ({website}).\n\n"
        f"{audit_summary.strip()}\n"
        f"{preview_line}\n"
        "Если идея полезна, я могу подготовить полный первый проект за 49–99 EUR. "
        "Сначала согласуем объём, обязательств по оплате за демо нет.\n\n"
        "Если это неактуально, ответьте «неактуально» — больше писать не буду.\n\n"
        f"С уважением,\n{BRAND}"
    )
    return subject, content


def follow_up_email(business_name: str, preview_url: str = "") -> tuple[str, str]:
    subject = f"Повторно: демо для {business_name}"
    preview_line = f"\nСсылка на демо: {preview_url}\n" if preview_url else ""
    content = (
        f"Здравствуйте!\n\n"
        f"Возвращаюсь к демо для {business_name}.{preview_line}\n"
        "Если сейчас это неактуально, просто ответьте «неактуально» — больше писать не буду.\n\n"
        f"{BRAND}"
    )
    return subject, content


def proposal_message(business_name: str, scope: str, amount: str = "49–99 EUR") -> str:
    """Create a post-interest proposal; payment is intentionally absent from cold email."""
    return (
        f"Здравствуйте!\n\n"
        f"Для {business_name} предлагаю следующий объём:\n{scope.strip()}\n\n"
        f"{payment_instructions(amount)}\n\n"
        "После подтверждения объёма и оплаты начинаю работу. "
        "Если что-то нужно изменить, согласуем это до оплаты."
    )
