"""Generate a safe static HTML preview from an approved research result."""

from __future__ import annotations

import html
import re
from pathlib import Path


def _first_line(content: str, fallback: str) -> str:
    for line in content.splitlines():
        clean = line.strip()
        if clean and not clean.startswith("Тип:") and not clean.startswith("Адресат:"):
            return clean[:140]
    return fallback


def generate_preview(output_dir: Path, approval: dict[str, str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", approval["id"].lower()).strip("-") or "preview"
    title = html.escape(approval.get("title", "Business website preview"))
    summary = html.escape(_first_line(approval.get("content", ""), "A clearer digital presence for your business."))
    target = html.escape(approval.get("target", ""))
    path = output_dir / f"{slug}.html"
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; font-family: Georgia, serif; background: #f5f1ea; color: #1e2925; }}
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; }}
main {{ width: min(960px, 88vw); padding: 72px 0; }}
.eyebrow {{ color: #b45f3c; font: 700 12px/1.2 system-ui, sans-serif; letter-spacing: .12em; text-transform: uppercase; }}
h1 {{ max-width: 760px; font-size: clamp(42px, 8vw, 92px); line-height: .95; margin: 18px 0 28px; font-weight: 500; }}
p {{ max-width: 580px; font: 18px/1.6 system-ui, sans-serif; color: #53615a; }}
a {{ display: inline-block; margin-top: 24px; padding: 14px 20px; background: #1e2925; color: #fff; text-decoration: none; font: 700 14px system-ui, sans-serif; }}
small {{ display: block; margin-top: 48px; color: #879189; font: 12px system-ui, sans-serif; }}
</style>
</head>
<body><main>
<div class="eyebrow">Preview for {target}</div>
<h1>{title}</h1>
<p>{summary}</p>
<a href="#contact">Start a conversation</a>
<small>Generated as a reviewable concept. No external publication was performed.</small>
</main></body></html>
""",
        encoding="utf-8",
    )
    return path


def generate_demo_preview(
    output_dir: Path,
    business_name: str,
    website: str,
    report: dict[str, object],
    niche_id: str,
    lead_id: str,
) -> Path:
    """Create a reviewable redesign of the lead's highest-value first screen."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_slug = re.sub(r"[^a-z0-9]+", "-", lead_id.lower()).strip("-") or "lead"
    title = html.escape(business_name.strip() or "Ваш бизнес")
    source_url = html.escape(website.strip())
    summary = html.escape(str(report.get("summary") or "Найдены точки роста для первого экрана."))
    weaknesses = report.get("weaknesses", [])
    if not isinstance(weaknesses, list):
        weaknesses = []
    weakness_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in weaknesses[:3])
    is_hospitality = "hospitality" in niche_id
    niche_label = "HoReCa" if is_hospitality else "Стоматология"
    action_label = "забронировать столик" if is_hospitality else "записаться на консультацию"
    service_label = "Меню и бронирование" if is_hospitality else "Услуги и запись"
    page_promise = (
        "Вкусный повод прийти сегодня — без лишних поисков и звонков."
        if is_hospitality
        else "Понятный путь к уверенной улыбке — от первого экрана до записи."
    )
    audit_items = weakness_items or "<li>Сделать ценность и следующий шаг заметнее.</li>"
    path = output_dir / f"{safe_slug}-demo.html"
    path.write_text(
        f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — демо FDA Solutions</title>
<style>
:root {{ font-family: Inter, system-ui, sans-serif; color: #18231f; background: #fff8f4; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
main {{ max-width: 1180px; margin: auto; padding: 24px 6vw 72px; }}
nav {{ display: flex; justify-content: space-between; align-items: center; color: #59665f; font-size: 14px; }}
nav strong {{ color: #18231f; letter-spacing: .08em; }}
.badge {{ padding: 8px 12px; border: 1px solid #efd8d0; border-radius: 999px; background: #fff; }}
.hero {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 48px; padding: 88px 0 58px; align-items: center; }}
.eyebrow {{ color: #b75f57; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; font-size: 12px; }}
h1 {{ font-family: Georgia, serif; font-size: clamp(44px, 7vw, 82px); line-height: .96; font-weight: 500; margin: 18px 0 24px; }}
p, li {{ color: #53615a; line-height: 1.6; font-size: 17px; }}
.cta {{ display: inline-block; margin-top: 18px; padding: 15px 22px; border-radius: 999px; background: #263c36; color: #fff; text-decoration: none; font-weight: 700; }}
.mock {{ background: #f4c8bf; border-radius: 30px; padding: 16px; box-shadow: 16px 18px 0 #f8ded8; }}
.mock-page {{ min-height: 390px; border-radius: 20px; background: #fff; padding: 26px; }}
.mock-page h2 {{ font: 500 40px/1 Georgia, serif; margin: 68px 0 14px; color: #263c36; }}
.mock-page p {{ font-size: 14px; margin: 0; }}
.mock-button {{ display: inline-block; margin-top: 22px; padding: 12px 16px; border-radius: 999px; background: #e9948b; color: #fff; font-size: 13px; }}
.section {{ padding: 58px 0 0; }}
.section h2 {{ font: 500 clamp(32px, 5vw, 58px)/1 Georgia, serif; margin: 12px 0 28px; }}
.cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
.card {{ background: #fff; border: 1px solid #efd8d0; border-radius: 22px; padding: 24px; }}
.card strong {{ display: block; margin-bottom: 10px; }}
.card p {{ margin: 0; font-size: 15px; }}
.audit {{ margin-top: 52px; background: #263c36; color: #fff; border-radius: 26px; padding: 28px; display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }}
.audit p, .audit li {{ color: #d8e3df; }}
small {{ color: #879189; }}
@media(max-width:800px) {{ .hero, .audit, .cards {{ grid-template-columns: 1fr; }} .hero {{ padding-top: 58px; }} }}
</style>
</head>
<body><main>
<nav><strong>{title}</strong><span class="badge">Redesign 1 экрана · {niche_label}</span></nav>
<section class="hero">
<div><div class="eyebrow">Концепт новой главной страницы</div>
<h1>{page_promise}</h1>
<p>{title}: {summary}</p>
<a class="cta" href="#contact">{action_label}</a></div>
<div class="mock"><div class="mock-page"><small>ПЕРВЫЙ ЭКРАН · {service_label}</small><h2>{title}</h2><p>{page_promise}</p><span class="mock-button">{action_label}</span></div></div>
</section>
<section class="section"><div class="eyebrow">Что изменено в концепте</div><h2>Не просто «новый дизайн» — новый путь к действию.</h2>
<div class="cards"><article class="card"><strong>Сразу понятно, для кого</strong><p>Заголовок и короткое обещание объясняют ценность до того, как посетитель начнёт искать детали.</p></article><article class="card"><strong>Один главный CTA</strong><p>Кнопка ведёт к нужному действию: записи, бронированию или запросу консультации.</p></article><article class="card"><strong>Сначала доверие</strong><p>Следующий экран можно наполнить отзывами, услугами, ценами и реальными фотографиями бизнеса.</p></article></div></section>
<section class="audit" id="contact"><div><strong>Точки роста исходной страницы</strong><p>{summary}</p><small>Источник: {source_url}</small></div>
<ul>{audit_items}</ul>
</section>
<small>Персональное demo FDA Solutions. Это концепт одного экрана для обсуждения, не публикация и не копия исходного сайта.</small>
</main></body>
</html>
""",
        encoding="utf-8",
    )
    return path
